#warning add gpl header

#ifdef HAVE_CONFIG_H
#include <config.h>
#endif

#include <gtk/gtk.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <X11/Xlib.h>
#include <X11/Xcursor/Xcursor.h>
#include <libgnomeui/libgnomeui.h>
#include <libgnomevfs/gnome-vfs.h>
#include <gconf/gconf.h>
#include <gconf/gconf-client.h>
#include <glade/glade.h>

void reload_tree(GtkWidget *tree, GtkListStore *store);
void size_changed();
GladeXML *main_window = NULL;
GConfClient *client;
XcursorImage * cursor = NULL;
char*current_theme = NULL;

typedef struct {
	XcursorImages *image;
	int pos;
} animation_struct;

animation_struct animations[4];

#warning move this into gconf
char *paths[] = {
	"/usr/share/cursors/xfree/",
	"/usr/X11R6/lib/X11/icons/",
	"/usr/Xorg/lib/X11/icons/",
	"/usr/local/share/icons/",
	"/usr/share/icons/",
	"%s/.icons/",
	NULL
};	

void open_theme_dir()
{
	GError	* error = NULL;
	char	* filename;
	
	filename = g_strdup_printf("file:///%s/.icons/", g_getenv("HOME"));
	gnome_url_show(filename,&error);
	g_free(filename);

	if (error)
	{
		gnome_warning_dialog (error->message);
		g_error_free (error);
	}
}


void extract_theme()
{
#if GTK_CHECK_VERSION(2,4,0)

	GtkWidget *fs = gtk_file_chooser_dialog_new ("Select a xcursor theme", NULL,
					GTK_FILE_CHOOSER_ACTION_OPEN,					     						GTK_STOCK_CANCEL, 
					GTK_RESPONSE_CANCEL,
					GTK_STOCK_OK, 
					GTK_RESPONSE_OK,
					NULL);	

#else 
	GtkWidget *fs = gtk_file_selection_new("Select a xcursor theme\n");
#endif
	char *path;
	switch(gtk_dialog_run(GTK_DIALOG(fs)))
	{
	case GTK_RESPONSE_OK:
		{
			gchar *filename = NULL;
			
#if GTK_CHECK_VERSION(2,4,0)
			filename = g_shell_quote(gtk_file_chooser_get_filename(GTK_FILE_CHOOSER(fs)));
#else
			filename = g_shell_quote(gtk_file_selection_get_filename(GTK_FILE_SELECTION(fs)));
#endif

		path = g_strdup_printf("file-roller --extract-to=%s/.icons/ %s", g_getenv("HOME"), 
				filename);
		g_free(filename);

		g_spawn_command_line_sync(path, NULL, NULL, NULL,NULL);
		gtk_list_store_clear(GTK_LIST_STORE(gtk_tree_view_get_model(GTK_TREE_VIEW(glade_xml_get_widget(main_window, "cursor_tree")))));
		
		reload_tree(glade_xml_get_widget(main_window, "cursor_tree"), 
				GTK_LIST_STORE(gtk_tree_view_get_model(GTK_TREE_VIEW(glade_xml_get_widget(main_window, "cursor_tree")))));
		}
	default:  break;

	}
	
	gtk_widget_destroy(GTK_WIDGET(fs));

}

char * get_current_theme()
{
	gint size;

	gchar *theme = gconf_client_get_string(client, "/desktop/gnome/peripherals/mouse/cursor_theme", NULL);
	
	size = gconf_client_get_int(client,"/desktop/gnome/peripherals/mouse/cursor_size", NULL);
	gtk_spin_button_set_value(GTK_SPIN_BUTTON(glade_xml_get_widget(main_window, "spin_size")), (int)size);

	return theme;
}

/* this free's the pixbuf memory */
/* this could be a direct call to g_free, but this was usefull for tracking 
 * memory */
void image_destroy(gchar *pixels)
{
	g_free(pixels);
}


GdkPixbuf *get_pixbuf_from_cursor_image(XcursorImage *image)
{
	GdkPixbuf *pixbuf;
	/* make room for the converted pixels */
	guchar *test = (guchar*)malloc(4*image->width*image->height*sizeof(guchar));
	/* we want it to be long enough */
	long int i =0;
	/* I am going to move pointers (atleast for test1) and I want to keep also a reference 
	 * to the first one.. so make a temp pointer that I move
	 */
	guchar *temp1=  test;
	/* this is just that I don't have to cast all the time */
	guchar *temp2 = (guchar *)image->pixels;
	/* set every entry to 0. not needed but it was handy for testing */
	memset(test, '0', 4*image->width*image->height*sizeof(guchar));
	
	/* convert the BGRA to RGBA */
	/* this does nothing more then swapping colors.. nasty but It has to be done */
	for(i=0;i < (image->height*image->width*4);i=i+4)
	{
#if G_BYTE_ORDER == G_LITTLE_ENDIAN
		/* if little endian then its BGRA*/
		*temp1++ = temp2[i+2];	/*R Red*/
		*temp1++ = temp2[i+1];	/*G GREEN*/
		*temp1++ = temp2[i];	/*B BLUE*/
		*temp1++ = temp2[i+3];	/*  A ALPHA*/		    
#else
		/* if big endian then its ARGB */
		/* This isn't tested yet */
		*temp1++ = temp2[i+1];	/*R Red*/
		*temp1++ = temp2[i+2];	/*G GREEN*/
		*temp1++ = temp2[i+3];	/*B BLUE*/
		*temp1++ = temp2[i];	/*  A ALPHA*/		    
#endif
	}
	/* load a pixbuf. it uses the memory from test so I pass a free function that will 
	 * be called when pixbuf is freeed 
	 */
	pixbuf = gdk_pixbuf_new_from_data((const guchar *)test, 
			GDK_COLORSPACE_RGB,
			TRUE,
			8,
			image->width,
			image->height,
			image->width*4,
			(GdkPixbufDestroyNotify)image_destroy,
			NULL);
	/* if failed to make pixbuf free the pixel buffer */
	if(pixbuf == NULL)
	{
		g_free(test);
	}
	return pixbuf;

}


void set_cursor(GtkTreeView *tre, gchar *name)
{
	gint size = gtk_spin_button_get_value_as_int(GTK_SPIN_BUTTON(glade_xml_get_widget(main_window, "spin_size")));

	gconf_client_set_string(client,"/desktop/gnome/peripherals/mouse/cursor_theme", name, NULL);
	gconf_client_set_int(client,"/desktop/gnome/peripherals/mouse/cursor_size", size, NULL);
}


void size_changed()
{
	GtkTreeSelection *selection;
	GtkTreeIter iter;
	GtkTreeModel *model = gtk_tree_view_get_model(GTK_TREE_VIEW(glade_xml_get_widget(main_window, "cursor_tree")));
	selection = gtk_tree_view_get_selection(GTK_TREE_VIEW(glade_xml_get_widget(main_window, "cursor_tree"))); 
	if(gtk_tree_selection_get_selected(selection, &model, &iter))
	{
		gchar *name;
		gtk_tree_model_get(model, &iter, 1, &name, -1);
		set_cursor(NULL, name);

	}
}

/* set the correct example images following the selection  */
void entry_selected(GtkTreeView *tree)
{
	GtkTreeSelection *selection;
	GtkTreeIter iter;
	GtkTreeModel *model = gtk_tree_view_get_model(tree);
	gint size = gtk_spin_button_get_value_as_int(GTK_SPIN_BUTTON(glade_xml_get_widget(main_window, "spin_size")));
	selection = gtk_tree_view_get_selection(tree); 
	if(gtk_tree_selection_get_selected(selection, &model, &iter))
	{
		gchar *name;
		gtk_tree_model_get(model, &iter, 1, &name, -1);
		
		if(animations[0].image != NULL)
		{
			XcursorImagesDestroy(animations[0].image);              		
		}
		animations[0].image= XcursorLibraryLoadImages("left_ptr",name, size);		
		animations[0].pos        = 0;                          

	
		if(animations[1].image != NULL)
		{
			XcursorImagesDestroy(animations[1].image);
		}
		animations[1].image= XcursorLibraryLoadImages("xterm",name,size);
		animations[1].pos        = 0;

		if(animations[2].image != NULL)
		{
			XcursorImagesDestroy(animations[2].image);
		}
		animations[2].image      = XcursorLibraryLoadImages("cross",name,size);
		animations[2].pos        =0;


		if(animations[3].image != NULL)
		{
			XcursorImagesDestroy(animations[3].image);
		}
		animations[3].image      = XcursorLibraryLoadImages("watch",name, size);
		animations[3].pos        =0;

		set_cursor(tree, name);

		if(current_theme != NULL)
		{
			g_free(current_theme);
		}
		current_theme = g_strdup(name);
		/* I never know if this is needed */
		g_free(name);
	}
}
/* read the cursors and display them in the list */
void reload_tree(GtkWidget *tree, GtkListStore *store)
{
	gchar	**iterator = NULL;
	gchar *dirname;
	GDir *directory;
	const gchar *name = NULL;
	GtkTreeIter iter;
	gint size = gtk_spin_button_get_value_as_int(GTK_SPIN_BUTTON(glade_xml_get_widget(main_window, "spin_size")));

	/* add the default themes */
	gtk_list_store_append(store, &iter);
	gtk_list_store_set(store, &iter, 1, "default", -1);
	if(current_theme != NULL && !strcmp(current_theme, "default"))
	{
		gtk_tree_selection_select_iter(                                  	
				gtk_tree_view_get_selection(GTK_TREE_VIEW(tree)),
				&iter);
	}                                                                        	
	
	for (iterator = paths; *iterator; iterator++)
	{
		dirname = g_strdup_printf(*iterator, g_getenv("HOME"));
		directory = g_dir_open(dirname, 0, NULL);
		
		while(directory != NULL && (name = g_dir_read_name(directory)) != NULL)		
		{
			GdkPixbuf *pixbuf;
			gchar *filename = g_strdup_printf("%s%s/cursors/", dirname, name);

			if(!g_file_test(filename, G_FILE_TEST_EXISTS))
			{
				g_free(filename);
				continue;
			}
			g_free(filename);
			cursor = XcursorLibraryLoadImage("left_ptr",name, size);
			if(cursor != NULL)
			{
				pixbuf = get_pixbuf_from_cursor_image(cursor);
				if(pixbuf == NULL)
				{
				}
				else
				{
					gtk_list_store_append(store, &iter);
					gtk_list_store_set(store, &iter, 0 ,pixbuf, 1, name, -1);
					g_object_unref(pixbuf);
					if(current_theme != NULL && !strcmp(current_theme, name))
					{
						gtk_tree_selection_select_iter(
								gtk_tree_view_get_selection(GTK_TREE_VIEW(tree)),
								&iter);
					}

				}
				XcursorImageDestroy(cursor);
			}
		}
		if(directory != NULL) 
		{
			g_dir_close(directory);
		}
		g_free(dirname);
	}
}

int update_animation()
{
	GdkPixbuf *pixbuf;
	if(animations[0].image && animations[0].image != NULL && animations[0].image->nimage != 0)
	{
		pixbuf = get_pixbuf_from_cursor_image(animations[0].image->images[animations[0].pos]);
		gtk_image_set_from_pixbuf(GTK_IMAGE(glade_xml_get_widget(main_window, "example_1")),
				pixbuf);
		g_object_unref(pixbuf);
		if(animations[0].image->nimage > animations[0].pos+1)
		{
			animations[0].pos++;
		}
		else animations[0].pos = 0;
	}
	else
	{
		gtk_image_set_from_stock(GTK_IMAGE(glade_xml_get_widget(main_window, "example_1")),
				GTK_STOCK_DIALOG_QUESTION, GTK_ICON_SIZE_LARGE_TOOLBAR);
	}

	if(animations[1].image && animations[1].image->images != NULL && animations[1].image->nimage != 0)
	{
		pixbuf = get_pixbuf_from_cursor_image(animations[1].image->images[animations[1].pos]);
		gtk_image_set_from_pixbuf(GTK_IMAGE(glade_xml_get_widget(main_window, "example_2")),
				pixbuf);
		g_object_unref(pixbuf);
		if(animations[1].image->nimage > animations[1].pos+1)
		{
			animations[1].pos++;                                                          	
		}
		else animations[1].pos = 0;
	}
	else
	{
		gtk_image_set_from_stock(GTK_IMAGE(glade_xml_get_widget(main_window, "example_2")),
				GTK_STOCK_DIALOG_QUESTION, GTK_ICON_SIZE_LARGE_TOOLBAR);
	}

	
	if(animations[2].image && animations[2].image != NULL && animations[2].image->nimage != 0)
	{
		pixbuf = get_pixbuf_from_cursor_image(animations[2].image->images[animations[2].pos]);
		gtk_image_set_from_pixbuf(GTK_IMAGE(glade_xml_get_widget(main_window, "example_3")),
				pixbuf);
		g_object_unref(pixbuf);
		if(animations[2].image->nimage > animations[2].pos+1)
		{
			animations[2].pos++;
		}
		else animations[2].pos = 0;
	}
	else
	{
		gtk_image_set_from_stock(GTK_IMAGE(glade_xml_get_widget(main_window, "example_3")),
				GTK_STOCK_DIALOG_QUESTION, GTK_ICON_SIZE_LARGE_TOOLBAR);
	}

	
	if(animations[3].image && animations[3].image != NULL && animations[3].image->nimage != 0)
	{
		pixbuf = get_pixbuf_from_cursor_image(animations[3].image->images[animations[3].pos]);
		gtk_image_set_from_pixbuf(GTK_IMAGE(glade_xml_get_widget(main_window, "example_4")),
				pixbuf);
		g_object_unref(pixbuf);
		if(animations[3].image->nimage > animations[3].pos+1)
		{                                                                                     	
			animations[3].pos++;
		}
		else animations[3].pos = 0;
	}                     
	else
	{
		gtk_image_set_from_stock(GTK_IMAGE(glade_xml_get_widget(main_window, "example_4")),
				GTK_STOCK_DIALOG_QUESTION, GTK_ICON_SIZE_LARGE_TOOLBAR);
	}

	

	return TRUE;
}

int main(int argc, char **argv)
{
	GtkCellRenderer *renderer;
	GtkTreeViewColumn *column;
	GtkWidget *tree;
	GtkListStore *store;

#ifdef ENABLE_NLS
	bindtextdomain (GETTEXT_PACKAGE, PACKAGE_LOCALE_DIR);
	bind_textdomain_codeset (GETTEXT_PACKAGE, "UTF-8");
	textdomain (GETTEXT_PACKAGE);
#endif

	gtk_init(&argc, &argv);
	/* needed for gnome_show_url */
	gnome_vfs_init();
	gconf_init(argc, argv, NULL);
	client  = gconf_client_get_default();

	main_window = glade_xml_new(GLADE_PATH"/gcursor.glade", "select_dialog", NULL);
	store       = gtk_list_store_new(2, GDK_TYPE_PIXBUF, GTK_TYPE_STRING);
	tree        = glade_xml_get_widget(main_window, "cursor_tree");
	gtk_tree_view_set_model(GTK_TREE_VIEW(tree), GTK_TREE_MODEL(store));

	renderer = gtk_cell_renderer_pixbuf_new();
	column = gtk_tree_view_column_new_with_attributes("Cursor", renderer, "pixbuf", 0, NULL);
	gtk_tree_view_append_column(GTK_TREE_VIEW(tree),column);
	renderer = gtk_cell_renderer_text_new();
	column = gtk_tree_view_column_new_with_attributes("Name", renderer, "text",1 , NULL);
	gtk_tree_view_append_column(GTK_TREE_VIEW(tree),column);

	glade_xml_signal_autoconnect(main_window);

	current_theme = get_current_theme();
	reload_tree(tree, store);	

	entry_selected(GTK_TREE_VIEW(tree));
	/* you can tweak the anymation speed here */
	g_timeout_add(150, (GSourceFunc)update_animation, NULL);
	gtk_dialog_run(GTK_DIALOG(glade_xml_get_widget(main_window, "select_dialog")));
	return 0;
}

