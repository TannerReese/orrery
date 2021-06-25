import math
import re

from typing import Tuple, Union

# Vector type alias for type hints
Vector = Tuple[float, float, float]

# Forward declaration of type
SpherePoint = None

class Angle:
	"""
	Represent an angle in multiple different conventions
	
	Attributes:
		__radians : float -- This angle in radians
	
	Properties:
		radians : float -- Get in radians
		degrees : float -- Get in degrees
		hms : (int, int, float) -- Get in HMS format
		    NOTE: `hours` greater than or equal to zero and less than 23
		hmsstr : str -- Get in HMS format as string
		dms : (int, int, float) -- Get in DMS format
		    NOTE: `degrees` greater than -180 and less than 180
		dmsstr : str -- Get in DMS format as string
	"""
	
	def __init__(self, *args, isdeg=False, isHMS=False):
		"""
		Construct an angle from any number of conventions
		
		Note that by convention, the components of the
		(d, m, s) tuple are all signed similarly
		
		Signature:
			Angle(radians: float) -- As radians
			Angle(radianStr: str) -- String parsable as radians
			    NOTE: May have optional 'r' / 'R' at end
			Angle(degrees: float, isdeg=True) -- As degrees
			Angle(degreeStr: str, isdeg=True) -- String parsable as degrees
			    NOTE: May have optional 'd' at end
			
			Angle(degrees: int, minutes: int, seconds: float) -- As Degrees-Minutes-Seconds
			Angle((degrees: int, minutes: int, seconds: float)) -- As Degrees-Minutes-Seconds Tuple
			Angle(dmsStr: str) -- String of the form   (+-)<DEGREES>d <MINUTES>m <SECONDS>s
			    EX:  -3d 14m 15.6s
			
			Angle(hours: int, minutes: int, seconds: float, isHMS=True) -- As Hours-Minutes-Seconds
			Angle((hours: int, minutes: int, seconds: float), isHMS=True) -- As Hours-Minutes-Seconds Tuple
			Angle(hmsStr: str) -- String of the form   <HOURS>h <MINUTES>m <SECONDS>s
			    EX:  16h 42m 23.04s
		"""
		
		# Address single argument case first
		if len(args) == 1:
			args = args[0]
			
			if type(args) in [float, int, str]:
				# Angle(radians: float)
				# Angle(radianStr: str)
				# Angle(degrees: float, isdeg=True)
				# Angle(degreeStr: str, isdeg=True)
				try:
					# Check for end character if string
					if type(args) == str:
						args = args.strip().lower()
						
						if args[-1] == 'd':
							isdeg, args = True, args[:-1]
						elif args[-1] == 'r':
							isdeg, args = False, args[:-1]
					
					
					self.__radians = float(args)
					
					# Convert from degrees if necessary
					if isdeg:
						self.__radians = math.radians(self.__radians)
					
					return  # Leave
				except ValueError:
					# Angle(dmsStr: str)
					# Angle(hmsStr: str, isHMS=True)
					# When string cannot be parsed as float
					# We assume it is dmsStr or hmsStr and wait to address it
					pass
				
			elif not hasattr(args, '__iter__'):  # If not an iterable then it doesn't match any signature
				# Angle((degrees: int, minutes: int, seconds: float))
				# Angle((hours: int, minutes: int, seconds: float), isHMS=True)
				raise TypeError('Angle only takes one argument if it is a float, int, str, or triple')
		
		if type(args) == str:  # Must be dmsStr or hmsStr
			# Angle(dmsStr: str)
			# Angle(hmsStr: str, isHMS=True)
			self.__radians = Angle.__parseHDMS(args)
			
		elif len(args) == 3:
			# Angle(degrees: int, minutes: int, seconds: float)
			# Angle(hours: int, minutes: int, seconds: float, isHMS=True)
			
			if isHMS:
				h, m, s = args
				
				# Ignore sign for HMS format
				h, m, s = abs(h), abs(m), abs(s)
				self.__radians = float((h + m / 60 + s / 3600) * math.pi / 12)
			else:
				d, m, s = args
				
				# Extract sign from degrees
				d, m, s, sign = abs(d), abs(m), abs(s), (-1 if d < 0 else 1)
				self.__radians = float(math.radians(sign * (d + m / 60 + s / 3600)))
			
		else:
			raise ValueError('Angle constructor takes either one or three positional arguments %i were given' % len(args))
	
	
	def __add__(self, other):
		""" Add two Angles together treating int / float as radians """
		
		if type(other) == int or type(other) == float:
			return Angle(self.__radians + other)
		elif isinstance(other, Angle):
			return Angle(self.__radians + other.__radians)
		else:
			raise TypeError("An Angle can only be added to another Angle or a floating point or integer")
	
	def __mul__(self, other):
		"""
		Mutliply some number int / float by this Angle
		NOTE: The Angle is moved to the range 0 to 2pi before multiplication
		"""
		
		if type(other) == int or type(other) == float:
			return Angle((self.__radians % (2 * math.pi)) * other)
		else:
			raise TypeError("An Angle can only be multiplied by an integer or floating point")
	
	
	@property
	def radians(self):
		return self.__radians
	
	@property
	def degrees(self):
		return math.degrees(self.__radians)
	
	
	@staticmethod
	def __splitBy60(number: float) -> (int, int, float):
		"""
		Split a floating point number into 3 base-60 digits
		with the last digit having potential decimals
		
		Args:
			number: float -- Number to separate
		
		Returns:
			(int, int, float) -- The integer part, 60th's, and 3600th's
			    NOTE: The sign of the number is placed on the first digit only
		"""
		
		# Extract sign
		number, sign = abs(number), (-1 if number < 0 else 1)
		
		# Get and Remove integer number of hours / degrees
		hd = int(number)
		number -= hd
		
		# Get and Remove integer number of minutes
		number *= 60
		m = int(number)
		number -= m
		
		# Get number of seconds
		s = number * 60
		
		return (sign * hd, m, s)
	
	@property
	def dms(self):
		# Make sure degrees falls in the range -180 to 180
		degrees = (math.degrees(self.__radians) + 180) % 360 - 180
		return Angle.__splitBy60(degrees)
	
	@property
	def dmsstr(self):
		return '%id %im %gs' % self.dms
	
	@property
	def hms(self):
		# Make sure hours falls in the range 0 to 24
		hours = (12 * self.__radians / math.pi) % 24
		return Angle.__splitBy60(hours)
	
	@property
	def hmsstr(self):
		return '%ih %im %gs' % self.hms
	
	def __str__(self):
		return str(self.__radians)
	
	
	# Compile Regular Expression for DMS / HMS angles
	__angleRE = re.compile('([+-]?)([0123]?\d{1,2})([hHdD])\s*([0-5]?\d)[mM]\s*([0-5]?\d(?:\.\d+)?)[sS]', re.IGNORECASE)
	
	# Parse HMS and DMS strings
	@staticmethod
	def __parseHDMS(angstr: str) -> float:
		"""
		Parse Right Ascension string in Hour-Minute-Second
		or Degree-Minute-Second form
		
		Args:
			angstr: str -- String following HMS or DMS format
			    EX:  -3d 15m 23.1s
			    EX:  16h 7m 5.43s
		
		Returns:
			float -- Angle in radians
		"""
		
		m = Angle.__angleRE.match(angstr)
		
		# When string doesn't match
		if m is None :
			raise ValueError('String "' + angstr + '" does not match HMS or DMS format')
		
		# Check that first character is 'h' or 'H' and not 'd' or 'D'
		isdms = 'd' == m.group(3).lower()
		
		# Check for sign
		sign = m.group(1)
		if len(sign) > 0 :
			if isdms:
				sign = 1 if sign == '+' else -1
			else:
				raise ValueError('HMS format is not signed')
		else:
			sign = 1
		
		# Extract and convert values
		hd, m, s = int(m.group(2)), int(m.group(4)), float(m.group(5))
		
		# Check that values fall in appropriate ranges
		if hd < 0 or (360 if isdms else 24) <= hd :
			if isdms:
				raise ValueError('Degrees must be between 0 and 359, inclusive')
			else:
				raise ValueError('Hours must be between 0 and 23, inclusive')
		elif m < 0 or 60 <= m :
			raise ValueError('Minutes must be between 0 and 59, inclusive')
		elif s < 0 or 60 <= s :
			raise ValueError('Seconds must be greater than or equal to 0 and less than 60')
		
		# Sum values to get fraction of circle
		degrees = s  # Start with seconds
		degrees = m + degrees / 60  # Add minutes
		
		if isdms:
			degrees = hd + degrees / 60  # Add degrees
		else:
			degrees = hd + degrees / 60  # Add hours
			degrees *= 15 # Convert to degrees (15 degrees per hour)
		
		# Convert to radians
		return math.radians(degrees)


class SpherePoint:
	"""
	Represent Location on a Sphere (2-Sphere)
	
	Conventions:
	The equator is the plane z = 0
	The meridian crosses the equator at (1, 0, 0)
	Longitude runs counter-clockwise around the zenith (0, 0, 1)
	
	Attributes:
		__lat : float -- Latitude of point / Angle off equator (in radians)
		__long : float -- Longitude of point / Angle off meridian (in radians) 
		__vector : Vector -- Vector corresponding to point on unit sphere
	
	Properties:
		lat : float -- getter for latitude in radians
		latd : float -- getter for latitude in degrees
		latAng : Angle -- getter for latitude as Angle object
		long : float -- getter for longitude in radians
		longd : float -- getter for longitude in degrees
		longAng : Angle -- getter for longitude as Angle object
		vector : Vector -- getter for unit vector
	"""
	
	def __init__(self, *args, isdeg: bool = False):
		"""
		Construct Point on Sphere from vector or latitude and longitude
		
		Signature:
			SpherePoint(lat, long) -- Latitude and Longitude
			SpherePoint(lat, long, isdeg=True) -- Latitude and Longitude in degrees
			SpherePoint((lat, long)) -- Latitude and Longitude as tuple
			SpherePoint((lat, long), isdeg=True) -- Latitude and Longitude as tuple in degrees
			SpherePoint(x, y, z) -- Vector as components
			SpherePoint((x, y, z)) -- Vector as tuple
			
			NOTE: The latitude and longitude may be provided as
			      a float in radians or as an Angle object
		"""
		
		if len(args) == 1 :
		# SpherePoint((lat, long))
		# SpherePoint((x, y, z))
			args = args[0]
		
		if len(args) == 3 :  # SpherePoint(x, y, z)
			x, y, z = args
			m = math.sqrt(x * x + y * y + z * z)  # Calculate magnitude to unitize vector
			if m == 0 :
				self.__vector = (1, 0, 0)
			else:
				self.__vector = (x / m, y / m, z / m)
			
			# Leave latitude and longitude uncalculated
			self.__lat, self.__long = None, None
		elif len(args) == 2 :  # SpherePoint(lat, long)
			self.__lat, self.__long = args
			
			# Convert from Angle or degrees to radians
			if isinstance(self.__lat, Angle):
				self.__lat = self.__lat.radians
			elif isdeg:
				self.__lat *= math.pi / 180
			
			if isinstance(self.__long, Angle):
				self.__long = self.__long.radians
			elif isdeg:
				self.__long *= math.pi / 180
			
			
			# Normalize Long to [-pi, pi)
			self.__long = (self.__long + math.pi) % (2 * math.pi) - math.pi
			# Normalize Lat to [-pi/2, +pi/2)
			self.__lat = (self.__lat + math.pi / 2) % (2 * math.pi) - math.pi / 2
			if self.__lat > math.pi / 2 and self.__lat < 3 * math.pi / 2 :
				self.__lat = math.pi - self.__lat
			
			# Leave vector uncalculated
			self.__vector = None
		elif len(args) == 0 :
			raise ValueError('Not Enough Arguments provided to SpherePoint')
		else:
			raise ValueError('Too Many Arguments provided to SpherePoint')
	
	@staticmethod
	def parseLatLong(string: str) -> SpherePoint:
		"""
		Construct a SpherePoint from a string of the form
			<LAT> [n|N|s|S], <LONG> [e|E|w|W]
		Where <LAT> and <LONG> are in one of the formats
			<DEGREES> [d|D] [<MINUTES> (m|M)] [<SECONDS> (s|S)]
			<RADIANS> (r|R)
		With any amount of whitespace (except within a number)
		
		Args:
			string : str  -- String to parse into SpherePoint
		
		Raises:
			ValueError -- When `string` is not formatted correctly
		"""
		
		# Allow for negative numbers to be passed on command line without being recognized as options
		string = string.replace('_', '-')
		
		# Get latitude and longitude strings
		latS, lngS = string.split(',')
		latS, lngS = latS.strip(), lngS.strip()  # Remove leading and trailing whitespace
		
		# Check for cardinal directions
		latSign = 1
		if latS[-1] == 's' or latS[-1] == 'S' :
			latSign = -1  # Invert direction of latitude
			latS = latS[:-1]  # Remove last character
		elif latS[-1] == 'n' or latS[-1] == 'N' :
			latS = latS[:-1]  # Remove last character
		
		lngSign = 1
		if lngS[-1] == 'w' or lngS[-1] == 'W' :
			lngSign = -1  # Invert direction of longitude
			lngS = lngS[:-1]  # Remove last character
		elif lngS[-1] == 'e' or lngS[-1] == 'E' :
			lngS = lngS[:-1]  # Remove last character
		
		# Parse Latitude & Longitude angle
		lat, lng = Angle(latS), Angle(lngS)
		
		return SpherePoint(lat * latSign, lng * lngSign, isdeg=True)
	
	
	
	# Calculate the latitude and longitude
	def __calc_latlong(self) -> None:
		x, y, z = self.__vector
		self.__long = (math.atan2(y, x) + math.pi) % (2 * math.pi) - math.pi
		
		# Get distance from z-axis
		d = math.sqrt(x * x + y * y)
		self.__lat = math.atan2(z, d)
	
	# Calculate the vector
	def __calc_vector(self) -> None:
		# Find height above xy-plane
		z = math.sin(self.__lat)
		lcos = math.cos(self.__lat)
		
		# Calculate xy-plane location
		x = lcos * math.cos(self.__long)
		y = lcos * math.sin(self.__long)
		self.__vector = (x, y, z)
	
	
	# Getters which calculate values when necessary
	@property
	def lat(self) -> float:
		if self.__lat is None:
			self.__calc_latlong()
		return self.__lat
	
	@property
	def latd(self) -> float:
		return math.degrees(self.lat)
	
	@property
	def latAng(self) -> Angle:
		return Angle(self.lat)
	
	@property
	def long(self) -> float:
		if self.__long is None:
			self.__calc_latlong()
		return self.__long
	
	@property
	def longd(self) -> float:
		return math.degrees(self.long)
	
	@property
	def longAng(self) -> Angle:
		return Angle(self.long)
	
	@property
	def vector(self) -> Tuple[float, float, float]:
		""" Get unit-length vector representing this point """
		if self.__vector is None:
			self.__calc_vector()	
		return self.__vector
	
	
	def geoformat(self):
		""" Convert SpherePoint to String in Geographic Coordinates """
		latdir = 'S' if self.lat < 0 else 'N'
		longdir = 'W' if self.long < 0 else 'E'
		return "%.7f %c, %.7f %c" % (abs(self.latd), latdir, abs(self.longd), longdir)
	
	def __str__(self):
		return "%.7fd ,  %.7fd" % (self.latd, self.longd)
	
	def __repr__(self):
		return f"SpherePoint({self.lat}, {self.long})"



# Forward declaration of type
Rotation = None

class Rotation:
	"""
	Represent Rotation in 3-space using Rotation Matrices
	
	Attributes:
		__mat : ((float, float, float), (float, float, float), (float, float, float)) -- Rows of Rotation Matrix as tuple
		__axis : (float, float, float) -- Unit Axis vector of rotation (if it has been calculated)
		__ang : float -- Angle of rotation, oriented by right-hand rule (if it has been calculated)
	"""
	
	def __init__(self, *args, mag2 : float = None):
		"""
		Create Rotation from Rodrigues vector, Axis-Angle, or SpherePoint and Angle
		
		Signature:
			Rotation((a, b, c), (d, e, f), (g, h, i)) -- rows of rotation matrix as tuples
			Rotation((x, y, z), angle) -- Axis as tuple with Angle
			Rotation(x, y, z, angle) -- Axis as components with Angle
			Rotation(pt : SpherePoint, angle) -- SpherePoint to use as Axis with Angle
		"""
		
		# Set magnitude squared to be potentially reclaculated later
		self.__mag2 = mag2
		
		if len(args) == 3 :  # Rotation((a, b, c), (d, e, f), (g, h, i))
			args = tuple(map(tuple, args))  # Convert rows to tuples
			if len(args[0]) == 3 and len(args[1]) == 3 and len(args[2]) == 3 :
				self.__mat = args
				self.__axis = None
				self.__ang = None
			else:
				raise ValueError('Rows of Rotation Matrix must have three entries each')
		elif len(args) == 2 :
			self.__mat = None
			if type(args[0]) == tuple or type(args[0]) == list :  # Rotation((ax, ay, az), angle)
				# Set Axis and Angle to convert later
				self.__axis = tuple(args[0])
				self.__ang = args[1]
			elif isinstance(args[0], SpherePoint) :  # Rotation(pt : SpherePoint, angle)
				# Set Axis and Angle to convert later
				self.__axis = args[0].vector
				self.__ang = args[1]
			else:
				raise TypeError('When called with two arguments, the First Argument must be an Axis vector or SpherePoint')
		elif len(args) == 4 :  # Rotation(ax, ay, az, angle)
			# Set Axis and Angle to convert later
			self.__axis = args[:3]
			self.__ang = args[3]
			self.__mat = None
		elif len(args) <= 1:
			raise ValueError('Not Enough Arguments given to Rotation')
		else:
		  	raise ValueError('Too Many Arguments given to Rotation')
		
		# Ensure that axis vector is of correct dimension
		if self.__axis is not None and len(self.__axis) != 3 :
			raise ValueError('Axis vector of Rotation must have three components')
		
		# Convert Axis-Angle to Rotation Matrix
		if self.__mat is None :
			c, s = math.cos(self.__ang), math.sin(self.__ang)
			vs = 1 - c  # versin(theta) = 1 - cos(theta)
			
			# Unitize axis vector
			x, y, z = self.__axis
			m = math.sqrt(x * x + y * y + z * z)
			if m == 0 :  # Catch when axis vector is zero
				raise ValueError('Axis vector must be non-zero')
			x, y, z = x / m, y / m, z / m
			self.__axis = (x, y, z)
			
			# First Row
			r1 = (c + x * x * vs, x * y * vs - z * s, x * z * vs + y * s)
			# Second Row
			r2 = (y * x * vs + z * s, c + y * y * vs, y * z * vs - x * s)
			# Third Row
			r3 = (z * x * vs - y * s, z * y * vs + x * s, c + z * z * vs)
			self.__mat = (r1, r2, r3)
			
		# Check that matrix is special orthogonal
		else:
			# Check determinant equal to one (orientation preserving)
			self.__check_special()
			
			# Check orthogonality
			self.__check_ortho()
	
	def __check_special(self) -> None:
		""" Raises ValueError when self.__mat has determinant not equal to one """
		
		# Calculate product of first row with determinants of minors
		det = self.__mat[0][0] * (self.__mat[1][1] * self.__mat[2][2] - self.__mat[2][1] * self.__mat[1][2])
		det -= self.__mat[0][1] * (self.__mat[1][0] * self.__mat[2][2] - self.__mat[2][0] * self.__mat[1][2])
		det += self.__mat[0][2] * (self.__mat[1][0] * self.__mat[2][1] - self.__mat[2][0] * self.__mat[1][1])
		
		# Check correct value
		if not math.isclose(1, det) :
			raise ValueError('Rotation Matrix must have determinant one, but det(R) = ' + str(det) + '\n' + str(self.__mat))
	
	def __check_ortho(self) -> None:
		""" Raises ValueError when self.__mat is not an orthogonal matrix """
		
		# Check normality (unit-length)
		if not all(map(lambda r: math.isclose(1, Rotation.__dot(r, r)), self.__mat)) :
			raise ValueError('Rows of Rotation Matrix must be unit-length')
		
		# Check orthogonality
		r1, r2, r3 = self.__mat
		d12, d23, d31 = Rotation.__dot(r1, r2), Rotation.__dot(r2, r3), Rotation.__dot(r3, r1)
		if not math.isclose(0, d12, abs_tol=1e-09) :
			raise ValueError('Rows of Rotation Matrix must orthogonal to each other ; Row1 * Row2 = ' + str(d12))
		elif not math.isclose(0, d23, abs_tol=1e-09) :
			raise ValueError('Rows of Rotation Matrix must orthogonal to each other ; Row2 * Row3 = ' + str(d23))
		elif not math.isclose(0, d31, abs_tol=1e-09) :
			raise ValueError('Rows of Rotation Matrix must orthogonal to each other ; Row3 * Row1 = ' + str(d31))
	
	# Dot product operator
	def __dot(v1: Vector, v2: Vector) -> float:
		return v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]
	
	
	@staticmethod
	def identity() -> Rotation:
		"""
		Generates Rotation that leaves all points fixed
		"""
		return Rotation(0, 0, 1, 0)
	
	@staticmethod
	def moveTo(begin: SpherePoint, end: SpherePoint, prop: float = 1) -> Rotation:
		"""
		Construct Rotation that moves the point `begin` to the point `end`
		
		Args:
			begin : SpherePoint -- starting point of rotation
			end : SpherePoint -- ending point of rotation
			prop : float -- proportion of way to go from begin to end must be in [0, 1]
			    NOTE: 0 -> no move, 0.5 -> half way to end, 1 -> all the way to end
		
		Returns:
			Rotation -- transformation that maps begin to end
		"""
		
		# Get unit vectors for points
		(ux, uy, uz), (vx, vy, vz) = begin.vector, end.vector
		
		# Find axis perpendicular to both points
		(cx, cy, cz) = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
		
		# Get cos(ang) using dot product to find angle
		ang = math.acos(ux * vx + uy * vy + uz * vz)
		
		return Rotation(cx, cy, cz, ang * prop)
	
	
	
	def __mul__(self, other: Rotation) -> Rotation:
		if not isinstance(other, Rotation):
			raise TypeError('Rotation can only be composed with another Rotation')
		
		# Take dot products between rows and columns
		return self.__div__(other.inverse)
	
	def __div__(self, other: Rotation) -> Rotation:
		""" Multiply Rotation by inverse of another Rotation """
		if not isinstance(other, Rotation):
			raise TypeError('Rotation can only be composed with another Rotation')
		
		# Take dot products between rows and rows
		args = tuple(tuple(Rotation.__dot(srow, orow) for orow in other.__mat) for srow in self.__mat)
		return Rotation(*args)
	
	__truediv__ = __div__
	
	
	@property
	def inverse(self) -> Rotation:
		""" Get inverse Rotation by taking transpose """
		# Get elements in matrix
		(s11, s12, s13), (s21, s22, s23), (s31, s32, s33) = self.__mat
		# Create columns
		return Rotation((s11, s21, s31), (s12, s22, s32), (s13, s23, s33))
		
	@property
	def axis(self) -> Vector:
		""" Get Axis vector around which this rotation rotates """
		if self.__axis is None:
			self.__axis = (self.__mat[2][1] - self.__mat[1][2], self.__mat[0][2] - self.__mat[2][0], self.__mat[1][0] - self.__mat[0][1])
		
		return self.__axis
	
	@property
	def angle(self) -> float:
		""" Get Angle by which this rotation rotates """
		if self.__ang is None:
			tr = self.__mat[0][0] + self.__mat[1][1] + self.__mat[2][2]
			self.__ang = math.acos((tr - 1) / 2)
		
		return self.__ang
	
	def rotate(self, vc: Vector) -> Vector:
		"""
		Rotate given vector using Rotation
		
		Arguments:
			vc : Vector -- 3-dimensional vector to rotate
		
		Returns:
			Vector -- 3-dimensional rotated vector
		"""
		
		# Convert SpherePoint to vector
		ispt = False
		if isinstance(vc, SpherePoint):
			vc = vc.vector
			ispt = True
		elif len(vc) != 3 :
			raise ValueError('Rotation can only rotate three-dimensional Vectors')
		
		# Apply rotation to vector
		vc = tuple(Rotation.__dot(r, vc) for r in self.__mat)
		
		if ispt:
			return SpherePoint(vc)
		else:
			return vc
	
	def __call__(self, other: Union[Vector, Rotation]) -> Union[Vector, Rotation]:
		"""
		If given a vector or SpherePoint then it rotates it.
		If given another Rotation then it conjugates it i.e.
			A -> R * A * R^T
		"""
		
		if isinstance(other, Rotation):
			return self.__mul__(other).__div__(self)
		else:
		 	return self.rotate(other)

