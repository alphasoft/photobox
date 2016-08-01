#
# $Id: FSM.py,v 1.2 2003/09/11 00:37:25 snyder Exp $
#
# File: FSM.py
# Purpose: A simple finite state machine class.
# Created: Dec, 1998, sss
#
# See __init__.py for a summary of this package.
#
# A FSM instance is constructed by specifying the initial state and the
# state transition table.  Transitions are then effected by calling the do()
# method.
#
# Format of the state transition table:
#
# TABLE = { state : STATEDESC, ... }
# STATEDESC = [(action, proc, newstate), ... ]
#  action is the name of the action.
#  newstate is the new state.
#  proc is a function to call.  The first two arguments it gets are
#  this object instance and the action name.
#  Any additional arguments to do() are passed to it as additional
#  args.  If proc is 1, nothing is called, and the transition is considered
#  to always be allowed.
#  proc should return a 2-element tuple: (STAT, RET).
#  If STAT is None, the transition is not really allowed; otherwise,
#  the transition is allowed.
#  If RET is noncallable, then that is the value returned from
#  do().  Otherwise, it is called (with no arguments), and the result
#  of this call is the return value of do().
#  Note that this function may call do().
#
#  If proc is a list, then all its elements are called in sequence
#  until we either reach the end or one returns false for STAT.
#  The RET value from the last function called is used; any previous
#  ones are ignored.
#
#  The values in proc may also be strings.  In that case, a class
#  should be passed into the FSM constructor.  The strings will
#  be looked up as attributes of that class as replaced by the
#  result.  This is useful in some cases where the table is generated
#  automatically (from a diagram, for example).  The table can then
#  be put into a base class of the complete FSM.  For example:
#
#    class My_FSM_Data:
#      S_INIT = 'init'
#      S_FINI = 'fini'
#      A_RUN = 'run'
#      state_table = { S_INIT : [ (A_RUN, 'doit', S_FINI) ],
#                      S_FINI : []}
#
#    class My_FSM (FSM, My_FSM_Data):
#      def __init__ (self):
#        FSM.__init__ (self, My_FSM.state_table, My_FSM.S_INIT, My_FSM)
#
#  Class My_FSM_Data then has no dependencies, and can be moved to a
#  separate source file.
#
#  The state and action names may be any python objects which can be
#  compared for equality; the state names, in addition, must be able
#  to be used as dictionary keys.  Strings will probably be appropriate
#  in most cases.
#


#
# Resolve a single procedure reference PROC within class CLS.
# If PROC is a string, look it up in CLS.
# Otherwise, just return PROC.
#
def _resolve_proc (proc, cls):
    if type (proc) == type (""):
        proc = getattr (cls, proc)
    return proc


#
# Resolve one set of procedure calls within class CLS.
# PROCS may be either a single procedure specification or a list of them.
#
def _resolve_procs1 (procs, cls):
    if type (procs) == type ([]):
        return [_resolve_proc (x, cls) for x in procs]
    return _resolve_proc (procs, cls)


class FSM:

    # A simple finite state machine class.

    # State:
    # __Xtable:
    #   The state transition table, as defined above.
    #
    # __state:
    #   The current FSM state.

    #
    # Constructor.
    # TABLE is the state transition table, and INITSTATE is the initial state.
    # If CLS is provided, it is used to resolve any string-valued
    # procedure names in the state table.
    #
    def __init__ (self, table, initstate, cls = None):
        self.__Xtable = table
        assert table.has_key (initstate)
        self.__state = initstate
        if cls:
            self.resolve_procs (cls)
        return


    #
    # Look up any string-valued procs in the state table in class CLS.
    #
    def resolve_procs (self, cls):
        for v in self.__Xtable.values():
            for i in range (len (v)):
                v[i] = (v[i][0], _resolve_procs1 (v[i][1], cls), v[i][2])
        return


    #
    # Return the current FSM state.
    #
    def state (self):
        return self.__state


    #
    # Return true if the current state has a transition for ACTION.
    #
    def can_do (self, action):
        table = self.__Xtable
        assert table.has_key (self.__state)
        for a in table[self.__state]:
            if a[0] == action:
                return 1

        # Couldn't find the action.
        return 0
        


    #
    # Carry out the FSM action ACTION.
    # Any additional args are passed to the transition routine.
    # Returns true if the transition was allowed, false otherwise.
    #
    def do (self, action, *args):
        table = self.__Xtable
        assert table.has_key (self.__state)
        for a in table[self.__state]:
            if a[0] == action:
                newstate = a[2]
                stat = a[1]
                ret = stat
                if type (stat) == type ([]):
                    for f in stat:
                        (stat, ret) = apply (f, (self, action,) + args)
                        if not stat:
                            break
                elif callable (stat):
                    stat, ret = apply (stat, (self, action,) + args)
                if stat:
                    # Transition is ok.
                    assert table.has_key (newstate)
                    self.__state = newstate
                if callable (ret):
                    ret = ret ()
                return ret

        # Couldn't find the action.
        return 0
    
    
    
