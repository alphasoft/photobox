gladedir	= $(datadir)/gcursor
glade_DATA	= gcursor.glade

applicationdir = $(prefix)/share/applications
application_in_files = gcursor.desktop.in
application_DATA = $(application_in_files:.desktop.in=.desktop)
@INTLTOOL_DESKTOP_RULE@

EXTRA_DIST	= $(glade_DATA) $(application_in_files)
