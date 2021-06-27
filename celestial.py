import math
import sys
from datetime import datetime, timedelta
from typing import Tuple

from sphere import Angle, SpherePoint, Rotation

Vector = Tuple[float, float, float]  # Three dimensional real vector

# Gravitation Constant in km^3 / (kg * s^2)
GRAVITATIONAL_CONSTANT = 6.6743015e-20

# Standard epoch of noon on Jan 1st, 2000
EPOCH_J2000 = datetime(2000, 1, 1, 12, 0, 0, 0)


class Rotator:
	"""
	Attributes:
		period : datetime.timedelta -- Sidereal Rotation period of object
		pole : SpherePoint -- Point on celestial sphere corresponding
		    to the angular momentum vector
		
		meridian : Angle -- Angle between the ascending node and meridian at the Epoch
		    NOTE: The ascending node, here, is the intersection point between
		    the rotational plane and the reference plane where the body is rotating
		    up through the reference plane
		epoch : datetime.datetime -- The time at which the meridian angle is measured
		
		__fromRef : Rotation -- Transformation from Rotator's equatorial frame to reference frame
		    NOTE: This transformation sends meridian point of the equator to the
		    reference direction thereby ignoring the offset of the meridian which
		    varies linearly with time
		__rotation : Rotation -- Transformation from time-varying horizontal frame to reference frame
		__time : datetime.datetime -- Time at which __rotation is valid
		__loc : SpherePoint -- Location on Rotator where __rotation is valid
	
	Properties:
		fromRef : Rotation -- Transformation from reference frame to Rotator's equatorial coordinates
	"""
	
	def __init__(self, period: timedelta,
		meridian: Angle, epoch: datetime = EPOCH_J2000,
		pole: SpherePoint = None,
		right_asc: Angle = None, decl: Angle = None
	):
		"""
		Construct a Rotator with the given parameters
		
		Args:
			period : datetime.timedelta -- Sidereal Rotation period
			meridian : Angle -- Angle between Ascending Node and Meridian at Epoch
			epoch : datetime.datetime -- Time at which meridian was measured
			
			pole : SpherePoint -- Pole of Rotator
			right_asc : -- Right Ascension of the North Pole
			decl : -- Declination of the North Pole
			NOTE: One of pole or (right_asc and decl) should be provided
		"""
		
		self.period = period
		self.meridian = meridian
		self.epoch = epoch
		
		if pole is not None:
			# Take pole if present
			self.pole = pole
		elif right_asc is not None and decl is not None:
			# Try to use right_asc and decl, otherwise
			self.pole = SpherePoint(decl, right_asc)
		else:
			self.pole = None
		
		# Defer calculation of transformations
		self.__fromRef = None
		self.__time, self.__loc, self.__rotation = None, None, None
	
	@property
	def fromRef(self) -> Rotation:
		""" Return transformation from the reference plane to the Rotator's equatorial coordinates """
		if self.__fromRef is None:
			if self.pole is None:
				raise ValueError("No pole present. Cannot calculate the reference transformation")
			
			# Create transformation from Reference coordinates to Rotator's Equatorial coordinates
			# Moving the ascending node of the Rotator onto the reference direction (origin)
			self.__fromRef = Rotation((0, 0, -1), self.pole.longAng + Angle.POS_RIGHT)
			
			# Rotate the Rotator's equator onto the reference plane
			self.__fromRef = Rotation((-1, 0, 0), self.pole.latAng.complement) * self.__fromRef
			
			# Move the Rotator's meridian at epoch onto the reference direction
			self.__fromRef = Rotation((0, 0, -1), self.meridian) * self.__fromRef
		
		return self.__fromRef
	
	@staticmethod
	def toHoriz(loc: SpherePoint) -> Rotation:
		# Move the longitude line of loc to the side opposite the origin
		rot = Rotation((0, 0, 1), loc.longAng.supplement)
		
		# Move the northward direction (Horizontal coordinates) onto the origin
		rot = Rotation((0, 1, 0), loc.latAng.complement) * rot
		return rot
	
	def rotation(self, time: datetime, loc: SpherePoint) -> Rotation:
		"""
		Get transformation from the reference frame to the
		horizontal frame for a given location and time
		
		Args:
			time : datetime.datetime -- Time at which to observe at
			loc : SpherePoint -- Location at which to observe from
		
		Returns:
			Rotation -- Transformation from reference frame to horizontal frame
		"""
		
		if self.__time == time and self.__loc == loc:
			return self.__rotation  # Return already calculated rotation
		
		# Transform from reference coordinates to this Rotator's equatorial coordinates
		rot = self.fromRef
		
		# Rotate the meridian into the correct offset for the time
		rot = Rotation((0, 0, -1), 2 * math.pi * ((time - self.epoch) / self.period)) * rot
		
		# Transform into horizontal coordinates for the location
		rot = Rotator.toHoriz(loc) * rot
		
		# Store rotation
		self.__time, self.__loc, self.__rotation = time, loc, rot
		
		return self.__rotation
	
	def __call__(self, time: datetime, loc: SpherePoint) -> Rotation:
		""" Alias for self.rotation(time, loc) """
		return self.rotation(time, loc)



class Orbit:
	"""
	The parameters to describe an orbit.
	
	The reference frame for the inclin, long_asc, and arg_peri
	are the ecliptical coordinates. The ecliptic plane as the
	reference plane and vernal point is the reference direction / origin
	
	Attributes:
		eccen : float -- Eccentricity of the Orbit
		semimajor : float -- Length of the Semimajor Axis in Kilometers
		
		inclin : Angle -- Inclination of the orbit from the reference plane
		long_asc : Angle -- Longitude of the Ascending Node
		    NOTE: The ascending node is the point where the orbital plane
		    and reference plane cross at which the object travels up through the reference plane.
		arg_peri : Angle -- The Argument of Periapsis which is the angle
		    between the longitude of the ascending node and the periapsis
		    traveling in the direction of orbit.
		
		mean_anom : Angle -- Mean anomaly of the object from the periapsis at the epoch
		epoch : datetime.datetime -- Time at which the mean anomaly was found
		
		__fromOrbit : Rotation -- Cached Transformation from orbital frame to reference frame
		    NOTE: The reference direction of the orbital frame is the periapsis
		          The reference plane of the orbital frame is the orbital plane
		__period : timedelta -- Amount of time necessary to revolve once (Sidereal)
		
		__position : (float, float, float) -- Cached location of the object at a given time
		__time : datetime.datetime -- Time at which the object was at __position
	"""
	
	def __init__(self,
		eccen: float, semimajor: float,
		inclin: Angle, long_asc: Angle, arg_peri: Angle,
		mean_anom: Angle, epoch: datetime = EPOCH_J2000,
		grav_param: float = None, mass: float = None, period: float = None
	):
		self.eccen = eccen
		self.semimajor = semimajor
		
		# Set angular values
		self.inclin = inclin
		self.long_asc = long_asc
		self.arg_peri = arg_peri
		
		# Set point data
		self.mean_anom = mean_anom
		self.epoch = epoch
		
		# Set gravitational parameter
		if mass is not None:
			# Mass takes precedence when present
			self.grav_param = GRAVITATIONAL_CONSTANT * mass
		elif grav_param is not None:
			self.grav_param = grav_param
		else:
			raise ValueError("Either grav_param or mass must be provided to find the Gravitational Parameter")
		
		# Defer calculation of orbital transform
		self.__fromOrbit = None
		
		# Set period if given
		if period is not None:
			self.__period = period
		else:
			self.__period = None
		
		# Create empty cache for position
		self.__time, self.__position = None, None
	
	@property
	def fromOrbit(self) -> Rotation:
		if self.__fromOrbit is None:
			# Calculate the transform
			# Move the periapsis off of the reference direction
			# And move the ascending node onto it
			self.__fromOrbit = Rotation((0, 0, 1), self.arg_peri)
			
			# Incline orbital plane off of reference plane
			self.__fromOrbit = Rotation((1, 0, 0), self.inclin) * self.__fromOrbit
			
			# Rotate ascending node off of the reference direction
			self.__fromOrbit = Rotation((0, 0, 1), self.long_asc) * self.__fromOrbit
		
		return self.__fromOrbit
	
	@property
	def period(self) -> timedelta:
		if math.isclose(self.grav_param, 0):
			return None
		elif self.__period is None:
			# Find period using semimajor axis and gravitational parameter
			self.__period = 2 * math.pi * self.semimajor * math.sqrt(self.semimajor / self.grav_param)
			# Convert to timedelta
			self.__period = timedelta(seconds=self.__period)
		
		return self.__period
	
	def position(self, time: datetime) -> Vector:
		"""
		Provide position of an object in this orbit at `time` as a 3-vector
		The reference frame for the output is ICRS / equatorial coordinates
		
		Args:
			time : datetime -- Time at which to find position
		
		Returns:
			(float, float, float) -- Three dimensional vector position in
			    reference frame coordinates
		"""
		
		# Return position if already calculated
		if time == self.__time:
			return self.__position
		
		# More quickly refer to values
		e = self.eccen
		e2 = e * e
		
		# Calculate the current mean anomaly in radians
		mean_anom = 2 * math.pi * ((time - self.epoch) / self.period) + self.mean_anom.radians
		
		# Calculate the true anomaly
		true_anom = mean_anom
		true_anom += (2 - e2 / 4) * e * math.sin(mean_anom)
		true_anom += 5 * e2 * math.sin(2 * mean_anom) / 4
		true_anom += 13 * e2 * e * math.sin(3 * mean_anom) / 12
		
		# Find radius
		radius = self.semimajor * (1 - e2) / (1 + e * math.cos(true_anom))
		
		# Get vector location in orbital coordinates
		vec = (radius * math.cos(true_anom), radius * math.sin(true_anom), 0)
		
		# Transform from orbital coordinates to ecliptical coordinates
		vec = self.fromOrbit(vec)
		
		# Send ecliptical coordinates to ICRS / equatorial
		vec = Rotation((1, 0, 0), math.radians(23.4365))(vec)
		
		# Save values to cache
		self.__position, self.__time = vec, time
		
		return self.__position
	
	def __call__(self, time: datetime) -> Tuple[float, float, float]:
		""" Alias for self.position(time) """
		return self.position(time)

