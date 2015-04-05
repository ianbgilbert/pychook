import marshal
import struct

interned_strs = []

class file_writter():
	def __init__(self, filename):
		self.writer = open(filename, 'wb')

	def write_int32(self, val):
		buff = chr(val & 0xFF) + chr((val & 0xFF00) >> 8) + chr((val & 0xFF0000) >> 16) + chr((val & 0xFF000000) >> 24)
		self.writer.write(buff)
	
	def write(self, data):
		self.writer.write(data)

	def close(self):
		self.writter.close()

class file_reader():
	def __init__(self, filename):
		self.reader = open(filename, 'rb')

	def unmarshal(self):
		t = self.reader.read(1)[0]

		if t == 'i': # int
			return pyc_int(self)
		elif t == '(':
			return pyc_tuple(self)
		elif t == 's':
			return pyc_str(self)
		elif t == 't':
			return pyc_str(self, interned=True)
		elif t == 'c':
			return pyc_code(self)
		elif t == 'R':
			return pyc_strref(self)
		elif t == 'N':
			return pyc_none(self)

	def read_int32(self):
		buff = self.reader.read(4)
		return ord(buff[0]) | ord(buff[1]) << 8 | ord(buff[2]) << 16 | ord(buff[3]) << 24
	
	def read(self, length):
		return self.reader.read(length)

class pyc_none():
	def __init__(self, f):
		pass

	def get_value(self):
		return None

	def get_type(self):
		return 'N'

	def dump(self, writter):
		writter.write(self.get_type())

class pyc_strref():
	def __init__(self, f):
		self.val = f.read_int32()
	
	def get_value(self):
		return self.val

	def get_str(self):
		return interened_strs[self.val]

	def get_type(self):
		return 'R'

	def dump(self, writter):
		writter.write(self.get_type())
		writter.write_int32(self.val)

class pyc_int():
	def __init__(self, f):
		self.val = f.read_int32()
	
	def get_value(self):
		return self.val

	def get_type(self):
		return 'i'

	def dump(self, writter):
		writter.write(self.get_type())
		writter.write_int32(self.val)

class pyc_str():
	def __init__(self, f, interned=False):
		length = f.read_int32()
		self.val = f.read(length)
		self.interned = interned
		if self.interned:
			interned_strs.append(self)

	def set_value(self, value):
		self.val = value

	def get_value(self):
		return self.val
	
	def get_type(self):
		if not self.interned:
			return 's'
		else:
			return 't'

	def dump(self, writter):
		writter.write(self.get_type())
		writter.write_int32(len(self.val))
		writter.write(self.val)

class pyc_tuple():
	def __init__(self, f):
		count = f.read_int32()
		self.values = []
		for i in range(count):
			self.values.append(f.unmarshal())

	def append(self, v):
		self.values.append(v)

	def get_len(self):
		return len(self.values)

	def get_value(self):
		return tuple(self.values)

	def get_type(self):
		return '('

	def dump(self, writter):
		writter.write(self.get_type())
		writter.write_int32(len(self.values))
		for v in self.values:
			v.dump(writter)

class pyc_code():
	
	def __init__(self, f):
		self.argcount = f.read_int32()
		self.nlocals = f.read_int32()
		self.stacksize = f.read_int32()
		self.flags = f.read_int32()
		self.code = f.unmarshal()
		self.consts = f.unmarshal()
		self.names = f.unmarshal()
		self.varnames = f.unmarshal()
		self.freevars = f.unmarshal()
		self.cellvars = f.unmarshal()
		self.filename = f.unmarshal()
		self.name = f.unmarshal()
		self.firstlineno = f.read_int32()
		self.lnotab = f.unmarshal()

	def hook_func(self, f):
		t = open('temp_func.bin', 'wb')
		marshal.dump(f.func_code, t)
		t.close()
		t = file_reader('temp_func.bin')
		t.read(1)
		c = pyc_code(t)
		self.hook(c)

	def hook(self, c):
		self.consts.append(c)
		func_index = self.consts.get_len() -1
		self.code.set_value('\x64' + chr(func_index & 0xFF) + chr((func_index & 0xFF00) >> 8) + '\x84\x00\x00\x83\x00\x00\x01' + self.code.get_value())

	def get_function(self, name):
		start = name.split('.', 1)[0]
		tail = None
		if len(name) > len(start):
			tail = name[len(start) + 1:]
	
		#print(tail)

		for c in self.consts.get_value():
			if c.get_type() == 'c':
				if c.get_name() == start:
					if tail == None:
						return c
					else:
						return c.get_function(tail)

	def get_name(self):
		return self.name.get_value()
	
	def get_type(self):
		return 'c'

	def dump(self, writter):
		writter.write(self.get_type())
		writter.write_int32(self.argcount)
		writter.write_int32(self.nlocals)
		writter.write_int32(self.stacksize)
		writter.write_int32(self.flags)
		self.code.dump(writter)
		self.consts.dump(writter)
		self.names.dump(writter)
		self.varnames.dump(writter)
		self.freevars.dump(writter)
		self.cellvars.dump(writter)
		self.filename.dump(writter)
		self.name.dump(writter)
		writter.write_int32(self.firstlineno)
		self.lnotab.dump(writter)

class PyBinary():
	def __init__(self, filename):
		f = file_reader(filename)
		self.magic = f.read_int32()
		self.timestamp = f.read_int32()
		self.code = f.unmarshal()

	def dump_to_file(self, filename):
		w = file_writter(filename)
		w.write_int32(self.magic)
		w.write_int32(self.timestamp)
		self.code.dump(w)
