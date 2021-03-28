import math
import sys

from typing import Tuple, Union

# Vector type alias for type hints
Vector = Tuple[float, float, float]

class SpherePoint:
	"""
	Represent Location on a Sphere (2-Sphere)
	
	Conventions:
	The equator is the plane z = 0
	The meridian crosses the equator at (1, 0, 0)
	Longitude runs counter-clockwise around the zenith (0, 0, 1)
	
	Attributes:
	    _lat : float -- Latitude of point / Angle off equator (in radians)
	    _long : float -- Longitude of point / Angle off meridian (in radians) 
	    _vector : Vector -- Vector corresponding to point on unit sphere
	
	Properties:
	    lat : float -- getter for latitude in radians
	    latd : float -- getter for latitude in degrees
	    long : float -- getter for longitude in radians
	    longd : float -- getter for longitude in degrees
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
		"""
		
		if len(args) == 1 :
		# SpherePoint((lat, long))
		# SpherePoint((x, y, z))
			args = args[0]
		
		if len(args) == 3 :  # SpherePoint(x, y, z)
			x, y, z = args
			m = math.sqrt(x * x + y * y + z * z)  # Calculate magnitude to unitize vector
			if m == 0 :
				self._vector = (1, 0, 0)
			else:
				self._vector = (x / m, y / m, z / m)
			
			# Leave latitude and longitude uncalculated
			self._lat, self._long = None, None
		elif len(args) == 2 :  # SpherePoint(lat, long)
			self._lat, self._long = args
			
			# Convert degrees to radians
			if isdeg:
				self._lat *= math.pi / 180
				self._long *= math.pi / 180
			
			# Normalize Long to [-pi, pi)
			self._long = (self._long + math.pi) % (2 * math.pi) - math.pi
			# Normalize Lat to [-pi/2, +pi/2)
			self._lat = (self._lat + math.pi / 2) % (2 * math.pi) - math.pi / 2
			if self._lat > math.pi / 2 and self._lat < 3 * math.pi / 2 :
				self._lat = math.pi - self._lat
			
			# Leave vector uncalculated
			self._vector = None
		elif len(args) == 0 :
			raise ValueError('Not Enough Arguments provided to SpherePoint')
		else:
			raise ValueError('Too Many Arguments provided to SpherePoint')
	
	
	
	# Calculate the latitude and longitude
	def _calc_latlong(self) -> None:
		x, y, z = self._vector
		self._long = (math.atan2(y, x) + math.pi) % (2 * math.pi) - math.pi
		
		# Get distance from z-axis
		d = math.sqrt(x * x + y * y)
		self._lat = math.atan2(z, d)
	
	# Calculate the vector
	def _calc_vector(self) -> None:
		# Find height above xy-plane
		z = math.sin(self._lat)
		lcos = math.cos(self._lat)
		
		# Calculate xy-plane location
		x = lcos * math.cos(self._long)
		y = lcos * math.sin(self._long)
		self._vector = (x, y, z)
	
	
	# Getters which calculate values when necessary
	@property
	def lat(self) -> float:
		if self._lat is None:
			self._calc_latlong()
		return self._lat
	
	@property
	def latd(self) -> float:
		return math.degrees(self.lat)
	
	@property
	def long(self) -> float:
		if self._long is None:
			self._calc_latlong()
		return self._long
	
	@property
	def longd(self) -> float:
		return math.degrees(self.long)
	
	@property
	def vector(self) -> Tuple[float, float, float]:
		""" Get unit-length vector representing this point """
		if self._vector is None:
			self._calc_vector()
		return self._vector


# Forward declaration of type
Rotation = None

class Rotation:
	"""
	Represent Rotation in 3-space using Rotation Matrices
	
	Attributes:
		_mat : ((float, float, float), (float, float, float), (float, float, float)) -- Rows of Rotation Matrix as tuple
	    _axis : (float, float, float) -- Unit Axis vector of rotation (if it has been calculated)
	    _ang : float -- Angle of rotation, oriented by right-hand rule (if it has been calculated)
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
		self._mag2 = mag2
		
		if len(args) == 3 :  # Rotation((a, b, c), (d, e, f), (g, h, i))
			args = tuple(map(tuple, args))  # Convert rows to tuples
			if len(args[0]) == 3 and len(args[1]) == 3 and len(args[2]) == 3 :
				self._mat = args
				self._axis = None
				self._ang = None
			else:
				raise ValueError('Rows of Rotation Matrix must have three entries each')
		elif len(args) == 2 :
			self._mat = None
			if type(args[0]) == tuple or type(args[0]) == list :  # Rotation((ax, ay, az), angle)
				# Set Axis and Angle to convert later
				self._axis = tuple(args[0])
				self._ang = args[1]
			elif isinstance(args[0], SpherePoint) :  # Rotation(pt : SpherePoint, angle)
				# Set Axis and Angle to convert later
				self._axis = args[0].vector
				self._ang = args[1]
			else:
				raise TypeError('When called with two arguments, the First Argument must be an Axis vector or SpherePoint')
		elif len(args) == 4 :  # Rotation(ax, ay, az, angle)
			# Set Axis and Angle to convert later
			self._axis = args[:3]
			self._ang = args[3]
			self._mat = None
		elif len(args) <= 1:
			raise ValueError('Not Enough Arguments given to Rotation')
		else:
		  	raise ValueError('Too Many Arguments given to Rotation')
		
		# Ensure that axis vector is of correct dimension
		if self._axis is not None and len(self._axis) != 3 :
			raise ValueError('Axis vector of Rotation must have three components')
		
		# Convert Axis-Angle to Rotation Matrix
		if self._mat is None :
			c, s = math.cos(self._ang), math.sin(self._ang)
			vs = 1 - c  # versin(theta) = 1 - cos(theta)
			
			# Unitize axis vector
			x, y, z = self._axis
			m = math.sqrt(x * x + y * y + z * z)
			if m == 0 :  # Catch when axis vector is zero
				raise ValueError('Axis vector must be non-zero')
			x, y, z = x / m, y / m, z / m
			self._axis = (x, y, z)
			
			# First Row
			r1 = (c + x * x * vs, x * y * vs - z * s, x * z * vs + y * s)
			# Second Row
			r2 = (y * x * vs + z * s, c + y * y * vs, y * z * vs - x * s)
			# Third Row
			r3 = (z * x * vs - y * s, z * y * vs + x * s, c + z * z * vs)
			self._mat = (r1, r2, r3)
			
		# Check that matrix is special orthogonal
		else:
			# Check determinant equal to one (orientation preserving)
			self._check_special()
			
			# Check orthogonality
			self._check_ortho()
	
	def _check_special(self) -> None:
		""" Raises ValueError when self._mat has determinant not equal to one """
		
		# Calculate product of first row with determinants of minors
		det = self._mat[0][0] * (self._mat[1][1] * self._mat[2][2] - self._mat[2][1] * self._mat[1][2])
		det -= self._mat[0][1] * (self._mat[1][0] * self._mat[2][2] - self._mat[2][0] * self._mat[1][2])
		det += self._mat[0][2] * (self._mat[1][0] * self._mat[2][1] - self._mat[2][0] * self._mat[1][1])
		
		# Check correct value
		if not math.isclose(1, det) :
			raise ValueError('Rotation Matrix must have determinant one, but det(R) = ' + str(det) + '\n' + str(self._mat))
	
	def _check_ortho(self) -> None:
		""" Raises ValueError when self._mat is not an orthogonal matrix """
		
		# Check normality (unit-length)
		if not all(map(lambda r: math.isclose(1, Rotation._dot(r, r)), self._mat)) :
			raise ValueError('Rows of Rotation Matrix must be unit-length')
		
		# Check orthogonality
		r1, r2, r3 = self._mat
		d12, d23, d31 = Rotation._dot(r1, r2), Rotation._dot(r2, r3), Rotation._dot(r3, r1)
		if not math.isclose(0, d12, abs_tol=1e-09) :
			raise ValueError('Rows of Rotation Matrix must orthogonal to each other ; Row1 * Row2 = ' + str(d12))
		elif not math.isclose(0, d23, abs_tol=1e-09) :
			raise ValueError('Rows of Rotation Matrix must orthogonal to each other ; Row2 * Row3 = ' + str(d23))
		elif not math.isclose(0, d31, abs_tol=1e-09) :
			raise ValueError('Rows of Rotation Matrix must orthogonal to each other ; Row3 * Row1 = ' + str(d31))
	
	# Dot product operator
	def _dot(v1: Vector, v2: Vector) -> float:
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
		        Note: 0 -> no move, 0.5 -> half way to end, 1 -> all the way to end
		
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
		args = tuple(tuple(Rotation._dot(srow, orow) for orow in other._mat) for srow in self._mat)
		return Rotation(*args)
	
	__truediv__ = __div__
	
	
	@property
	def inverse(self) -> Rotation:
		""" Get inverse Rotation by taking transpose """
		# Get elements in matrix
		(s11, s12, s13), (s21, s22, s23), (s31, s32, s33) = self._mat
		# Create columns
		return Rotation((s11, s21, s31), (s12, s22, s32), (s13, s23, s33))
		
	@property
	def axis(self) -> Vector:
		""" Get Axis vector around which this rotation rotates """
		if self._axis is None:
			self._axis = (self._mat[2][1] - self._mat[1][2], self._mat[0][2] - self._mat[2][0], self._mat[1][0] - self._mat[0][1])
		
		return self._axis
	
	@property
	def angle(self) -> float:
		""" Get Angle by which this rotation rotates """
		if self._ang is None:
			tr = self._mat[0][0] + self._mat[1][1] + self._mat[2][2]
			self._ang = math.acos((tr - 1) / 2)
		
		return self._ang
	
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
		vc = tuple(Rotation._dot(r, vc) for r in self._mat)
		
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

