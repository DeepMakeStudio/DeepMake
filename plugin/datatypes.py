import json

class Text():
    default = None
    max_length = None
    help = None
    optional = None

    def __init__(self, default=None, max_length=None, help=None, optional=None):
        self.default = default
        self.max_length = max_length
        self.help = help
        self.optional = optional

    @property
    def data(self):
        return {"default": self.default, "help": self.help, "max_length": self.max_length, "optional": self.optional}

    @property
    def __str__(self):
        return "Text" + json.dumps({k: v for k, v in self.data.items() if v is not None}).replace('{','(').replace('}',')').replace(': ','=').replace('"','')

    @property
    def __dict__(self):
        return {k: v for k, v in self.data.items() if v is not None}

class Image():
    Height = None
    Width = None
    channels = "RGB"
    dtype = "float32"
    help = None
    optional = None

    def __init__(self, Height=None, Width=None, channels="RGB", dtype="float32", help=None, optional=None):
        self.Height = Height
        self.Width = Width
        self.channels = channels
        self.dtype = dtype
        self.help = help
        self.optional = optional
    
    @property
    def data(self):
        return {"Height": self.Height, "Width": self.Width, "channels": self.channels, "dtype": self.dtype, "help": self.help, "optional": self.optional}

    def __str__(self):
        return "Image" + json.dumps({k: v for k, v in self.data.items() if v is not None}).replace('{','(').replace('}',')').replace(': ','=').replace('"','')

    def __dict__(self):
        return {k: v for k, v in self.data.items() if v is not None}

class Boolean():
    default = None
    help = None
    optional = None

    def __init__(self, default=None, help=None, optional=None):
        self.default = default
        self.help = help
        self.optional = optional

    @property
    def data(self):
        return {"default": self.default, "help": self.help, "optional": self.optional}

    @property
    def __str__(self):
        return "Bool" + json.dumps({k: v for k, v in self.data.items() if v is not None}).replace('{','(').replace('}',')').replace(': ','=').replace('"','')

    @property
    def __dict__(self):
        return {k: v for k, v in self.data.items() if v is not None}

class Integer():
    default = None
    min = None
    max = None
    help = None
    optional = None

    def __init__(self, default=None, min=None, max=None, help=None, optional=None):
        self.default = default
        self.min = min
        self.max = max
        self.help = help
        self.optional = optional

    @property
    def data(self):
        return {"default": self.default, "min": self.min, "max": self.max, "help": self.help, "optional": self.optional}

    @property
    def __str__(self):
        return "Int" + json.dumps({k: v for k, v in self.data.items() if v is not None}).replace('{','(').replace('}',')').replace(': ','=').replace('"','')

    @property
    def __dict__(self):
        return {k: v for k, v in self.data.items() if v is not None}

class Point():
    x = None
    y = None
    relative = None
    help = None
    optional = None

    def __init__(self, x=None, y=None, relative=Boolean(default=False, help="Whether the point is relative to the image size or pixelwise"), help=None, optional=None):
        self.x = x
        self.y = y
        self.relative = relative
        self.help = help
        self.optional = optional

    @property
    def data(self):
        return {"x": self.x, "y": self.y, "relative": self.relative, "help": self.help, "optional": self.optional}

    @property
    def __str__(self):
        return "Point" + json.dumps({k: v for k, v in self.data.items() if v is not None}).replace('{','(').replace('}',')').replace(': ','=').replace('"','')

    @property
    def __dict__(self):
        return {k: v for k, v in self.data.items() if v is not None}

class Box():
    top_left = None
    bottom_right = None
    relative = None
    help = None
    optional = None

    def __init__(self, top_left=None, bottom_right=None, relative=Boolean(default=False, help="Whether the box is relative to the image size or pixelwise"), help=None, optional=None):
        self.top_left = top_left
        self.bottom_right = bottom_right
        self.relative = relative
        self.help = help
        self.optional = optional

    @property
    def data(self):
        return {"top_left": self.top_left, "bottom_right": self.bottom_right, "relative": self.relative, "help": self.help, "optional": self.optional}

    @property
    def __str__(self):
        return "Box" + json.dumps({k: v for k, v in self.data.items() if v is not None}).replace('{','(').replace('}',')').replace(': ','=').replace('"','')

    @property
    def __dict__(self):
        return {k: v for k, v in self.data.items() if v is not None}

class Float():
    default = None
    min = None
    max = None
    dtype = "float32"
    help = None
    optional = None

    def __init__(self, default=None, min=None, max=None, dtype="float32", help=None, optional=None):
        self.default = default
        self.min = min
        self.max = max
        self.dtype = dtype
        self.help = help
        self.optional = optional

    @property
    def data(self):
        return {"default": self.default, "min": self.min, "max": self.max, "dtype": self.dtype, "help": self.help, "optional": self.optional}

    @property
    def __str__(self):
        return "Float" + json.dumps({k: v for k, v in self.data.items() if v is not None}).replace('{','(').replace('}',')').replace(': ','=').replace('"','')

    @property
    def __dict__(self):
        return {k: v for k, v in self.data.items() if v is not None}

class List():  #TODO define the types that can be in the list
    default = None
    help = None
    optional = None

    def __init__(self, default=None, help=None, optional=None):
        self.default = default
        self.help = help
        self.optional = optional

    @property
    def data(self):
        return {"default": self.default, "help": self.help, "optional": self.optional}

    @property
    def __str__(self):
        return "List" + json.dumps({k: v for k, v in self.data.items() if v is not None}).replace('{','(').replace('}',')').replace(': ','=').replace('"','')

    @property
    def __dict__(self):
        return {k: v for k, v in self.data.items() if v is not None}
