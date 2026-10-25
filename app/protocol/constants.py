"""
Synergy / Barrier Protocol Constants (Version 1.6 compatible).
"""

PROTOCOL_MAJOR_VERSION = 1
PROTOCOL_MINOR_VERSION = 6
DEFAULT_PORT = 24800
DEFAULT_WEB_PORT = 24801

# Handshake greetings
MSG_HELLO_BARRIER = "Barrier%2i%2i"
MSG_HELLO_SYNERGY = "Synergy%2i%2i"
MSG_HELLO_BACK_BARRIER = "Barrier%2i%2i%s"
MSG_HELLO_BACK_SYNERGY = "Synergy%2i%2i%s"

# Control codes (4 bytes ASCII)
MSG_C_NOOP = "CNOP"
MSG_C_CLOSE = "CBYE"
MSG_C_ENTER = "CINN"          # CINN%2i%2i%4i%2i (x, y, seq, mask)
MSG_C_LEAVE = "COUT"          # COUT
MSG_C_CLIPBOARD = "CCLP"      # CCLP%1i%4i
MSG_C_SCREEN_SAVER = "CSEC"   # CSEC%1i
MSG_C_RESET_OPTIONS = "CROP"  # CROP
MSG_C_INFO_ACK = "CIAK"       # CIAK
MSG_C_KEEP_ALIVE = "CALV"     # CALV

# Data codes
MSG_D_KEY_DOWN = "DKDN"       # DKDN%2i%2i%2i (key, mask, code)
MSG_D_KEY_REPEAT = "DKRP"     # DKRP%2i%2i%2i%2i (key, mask, count, code)
MSG_D_KEY_UP = "DKUP"         # DKUP%2i%2i%2i (key, mask, code)
MSG_D_MOUSE_DOWN = "DMDN"     # DMDN%1i (button)
MSG_D_MOUSE_UP = "DMUP"       # DMUP%1i (button)
MSG_D_MOUSE_MOVE = "DMMV"     # DMMV%2i%2i (x, y)
MSG_D_MOUSE_REL_MOVE = "DMRM" # DMRM%2i%2i (dx, dy)
MSG_D_MOUSE_WHEEL = "DMWM"    # DMWM%2i%2i (xDelta, yDelta)
MSG_D_CLIPBOARD = "DCLP"      # DCLP%1i%4i%1i%s (id, seq, mark, data)
MSG_D_INFO = "DINF"           # DINF%2i%2i%2i%2i%2i%2i%2i (x, y, w, h, warp, mx, my)
MSG_D_SET_OPTIONS = "DSOP"    # DSOP%4I
MSG_D_FILE_TRANSFER = "DFTR"  # DFTR%1i%s
MSG_D_DRAG_INFO = "DDRG"      # DDRG%2i%s

# Query & Errors
MSG_Q_INFO = "QINF"
MSG_E_INCOMPATIBLE = "EICV"
MSG_E_BUSY = "EBSY"
MSG_E_UNKNOWN = "EUNK"
MSG_E_BAD = "EBAD"

# Directions
DIR_NO = 0
DIR_LEFT = 1
DIR_RIGHT = 2
DIR_TOP = 3
DIR_BOTTOM = 4

# Mouse buttons
BUTTON_LEFT = 1
BUTTON_MIDDLE = 2
BUTTON_RIGHT = 3
BUTTON_EXTRA1 = 4
BUTTON_EXTRA2 = 5

# Modifier masks
MODIFIER_SHIFT = 0x0001
MODIFIER_CONTROL = 0x0002
MODIFIER_ALT = 0x0004
MODIFIER_META = 0x0008
MODIFIER_SUPER = 0x0010
MODIFIER_ALT_GR = 0x0020
MODIFIER_CAPS_LOCK = 0x1000
MODIFIER_NUM_LOCK = 0x2000
MODIFIER_SCROLL_LOCK = 0x4000
