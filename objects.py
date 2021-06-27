import xml.etree.ElementTree as xml
 
from datetime import datetime, timedelta
from typing import Callable, List, Union, Tuple
from enum import unique, Enum

from sphere import Angle, SpherePoint
from utils import fromXML, NamedMixin
from celestial import EPOCH_J2000, Orbit, Rotator

Vector = Tuple[float, float, float]  # Three dimensional real vector

# Type declarations to avoid imports
Observer = None
Rotation = None

BodyType = None  # Forward declaration

@unique
class BodyType(Enum):
	SUN = ('Sun', '<S>')
	PLANET = ('Planet', '[Pl]')
	MOON = ('Moon', '[m]')
	DWARF_PLANET = ('Dwarf Planet', '[d]')
	ASTEROID = ('Asteroid', '[a]')
	COMET = ('Comet', '[c]')
	
	def __init__(self, id, symbol):
		self.id = id
		self.symbol = symbol
	
	@staticmethod
	def fromStr(name: str) -> BodyType:
		name = name.lower()  # Ignore Case
		for tp in list(BodyType):
			if tp.id.lower() == name:
				return tp
		
		raise ValueError("No Body Type with identifier '%s'" % name)

# Forward declaration of Body
Body = None

class Body(NamedMixin):
	"""
	Attributes:
		name : str -- Name of object
		aliases : [str] -- Other names for this object
		type : BodyType -- Type of object
		
		orbit : Orbit -- Orbit that this object follows around its parent
		rotator : Rotator -- Object modelling the rotation of this body
		parent : Body -- Parent body around which this orbits
		    NOTE: If None then this body is the primary body
		
		mass : float -- Mass of this object in Kilograms
		mean_radius : float -- Mean Radius of this object in Kilometers
		density : float -- Density of this object in Grams per milliliter
		
		__position : Vector -- Cached position of body at `__time`
		__time : datetime -- Time for which `__position` is valid
	"""
	
	@fromXML('name', '@name', required=True)
	@fromXML('aliases', 'alias', multiple=True)
	@fromXML('type', '@type', required=True, parser=BodyType.fromStr)
	@fromXML('parentName', '@parent')
	@fromXML('symbol', '@symbol')
	
	# Orbital Parameters
	@fromXML('eccen', 'orbit/@eccentricity', required=True, parser=float)
	@fromXML('semimajor', 'orbit/@semimajor', required=True, parser=float)
	@fromXML('period', 'orbit/@period', parser=lambda s: timedelta(seconds=float(s)))
	# Angular orbital parameters (default to degrees)
	@fromXML('inclin', 'orbit/@inclination', required=True, parser=lambda s: Angle(s, isdeg=True))
	@fromXML('long_asc', 'orbit/@longitude-ascending', required=True, parser=lambda s: Angle(s, isdeg=True))
	@fromXML('arg_peri', 'orbit/@argument-periapsis', required=True, parser=lambda s: Angle(s, isdeg=True))
	# Identify phase of orbit
	@fromXML('mean_anom', 'orbit/point/@mean-anomaly', required=True, parser=lambda s: Angle(s, isdeg=True))
	@fromXML('epoch', 'orbit/point/@epoch', parser=datetime.fromisoformat, default=EPOCH_J2000)
	
	# Rotational Parameters
	@fromXML('rot_period', 'rotation/@period', parser=lambda s: timedelta(seconds=float(s)))
	@fromXML('pole_ra', 'rotation/pole/@right-asc', parser=lambda s: Angle(s, isdeg=True))
	@fromXML('pole_dec', 'rotation/pole/@decl', parser=lambda s: Angle(s, isdeg=True))
	# Identify phase of rotation
	@fromXML('meridian', 'rotation/point/@meridian', parser=lambda s: Angle(s, isdeg=True))
	@fromXML('rot_epoch', 'rotation/point/@epoch', parser=datetime.fromisoformat, default=EPOCH_J2000)
	
	@fromXML('mass', 'physical/@mass', parser=float)
	@fromXML('mean_radius', 'physical/@mean-radius', parser=float)
	@fromXML('density', 'physical/@density', parser=float)
	def __init__(self,
		# Not provided by XML
		getBody: Callable[[str], Body] = None, parent: Body = None,
		**prms  # XML Parameters
	):
		# Convert prms into namespace-like object
		prms = type('', (), prms)()
		
		self.initNames(prms.name, prms.aliases)
		self.type = prms.type
		
		# Set symbol if given
		if prms.symbol is None:
			self.symbol = self.type.symbol
		else:
			self.symbol = prms.symbol
		
		# Set parent body
		if parent is not None:
			# Use parent if provided
			self.parent = parent
		elif prms.parentName is None:
			# Primary body has no orbit
			self.parent = None
		else:
			# Use getBody method to find object corresponding to parentName
			if getBody is None:
				raise ValueError("No getBody method provided to identify parentName '%s' of body '%s'" % (parentName, name))
			
			self.parent = getBody(prms.parentName)
		
		# Construct orbit from parameters
		parentMass = 0  # Default to dummy value of mass if no parent present
		if self.parent is not None and self.parent.mass is not None:
			parentMass = self.parent.mass
		
		self.orbit = Orbit(
			prms.eccen, prms.semimajor,
			prms.inclin, prms.long_asc, prms.arg_peri,
			prms.mean_anom, prms.epoch,
			mass=parentMass, period=prms.period
		)
		
		# Constructor rotator from parameters
		self.rotator = Rotator(prms.rot_period,
			prms.meridian, prms.rot_epoch,
			right_asc=prms.pole_ra, decl=prms.pole_dec
		)
		
		# Set physical parameters
		self.mass = prms.mass
		self.mean_radius = prms.mean_radius
		self.density = prms.density
		
		# Make empty cache for position
		self.__time, self.__position = None, None
	
	
	def position(self, time: datetime) -> Vector:
		"""
		Return position of this body in the reference coordinates
		
		Args:
			time : datetime -- Time at which to find position
		
		Returns:
			(float, float, float) -- Three dimensional vector position in
			    reference frame coordinates
		"""
		
		if self.parent is None:
			# Return origin if primary body
			return (0, 0, 0)
		
		# Returned cached value if available
		if time == self.__time:
			return self.__position
		
		# Get offset from parent body
		(x, y, z) = self.orbit(time)
		# Get parent body's location
		(px, py, pz) = self.parent.position(time)
		
		# Add them and cache the result
		self.__time, self.__position = time, (x + px, y + py, z + pz)
		return self.__position
	
	
	def __str__(self, fields: List[str] = None, observer: Observer = None) -> str:
		"""
		Create info string for this Body
		
		Args:
			fields : [str] -- List of field names that should be included
			    in the info. These include the fields of Stellar, as well as
			    'altaz' if the Altitude & Azimuth should be found and
			    'point' if the Right Ascension & Declination should be found
			    NOTE: If None then all fields are provided
			
			observer : Observer -- Object containing the time, location, and body to view from
			    NOTE: Must be given to get Altitude & Azimuth (altaz) or RA & Dec (point)
		
		Returns:
			str -- Informational String
		"""
		
		# Ignore case on fields
		if fields is not None:
			fields = {f.lower() for f in fields}
		
		def hasField(obj, f):
			""" Check whether obj has a non-None field """
			return hasattr(obj, f) and getattr(obj, f) is not None
		
		def doField(f):
			""" Check whether a field should be printed """
			return fields is None or f in fields
		
		# Accumulate string
		info = self.name  # Show name
		# Show parent body name
		if doField('parent') and hasField(self, 'parent'):
			info += '    (%s)' % self.parent.name
		info += '\n'
		
		if doField('aliases') and len(self.aliases) > 0:  # Print Other Names
			info += '  |  '.join(self.aliases) + '\n'
		
		if observer is not None:
			# Get apparent location of body in reference coordinates
			radec = observer.toRef(self)
			if radec is not None:  # Check that the radec is displayable
				# Print Altitude & Azimuth if toView transform is provided
				if doField('altaz'):
					pt = observer.toHoriz(radec)  # Get horizontal coordinates of point
					info += "(Alt, Az):  %fd ,  %fd" % (pt.latd, (-pt.longd) % 360) + '\n'  # Altitude & Azimuth in degrees
				
				if doField('point'):  # Print Right Ascension and Declination
					info += "(RA, Dec):  %s ,  %s\n" % (radec.longAng.hmsstr, radec.latAng.dmsstr)
		
		# Show Orbital parameters
		if doField('eccen'):
			info += "Eccentricity: %g\n" % self.orbit.eccen
		
		if doField('semimajor'):
			info += "Semimajor Axis: %g km\n" % self.orbit.semimajor
		
		if doField('inclin'):
			info += "Inclination: %g degrees\n" % self.orbit.inclin.degrees
		
		if doField('long_asc'):
			info += "Longitude of the Ascending Node: %g degrees\n" % self.orbit.long_asc.degrees
		
		if doField('arg_peri'):
			info += "Argument of Periapsis: %g degrees\n" % self.orbit.arg_peri.degrees
		
		if doField('period') and hasField(self, 'parent'):
			info += "Orbital Period: %s\n" % str(self.orbit.period)
		
		# Show Rotational parameters
		if doField('rot_period') and hasField(self.rotator, 'rot_period'):
			info += "Sidereal Rotation Period: %s\n" % str(self.rotator.rot_period)
		
		if hasField(self.rotator, 'pole'):
			if doField('pole'):
				pole = self.rotator.pole
				info += "Pole (RA, Dec): %s ,  %s\n" % (pole.longAng.hmsstr, pole.latAng.dmsstr)
		
		# Show Physical quantities
		if doField('mass'):
			info += "Mass: %g kg \n" % self.mass
		
		if doField('mean-radius'):
			info += "Mean Radius: %g km \n" % self.mean_radius
		
		if doField('density'):
			info += "Density: %g g/mL\n" % self.density
		
		return info
	




StellarType = None  # Forward declaration

@unique
class StellarType(Enum):
	STAR = ('Star', '*')
	NEBULA = ('Nebula', '~N~')
	OPEN_CLUSTER = ('Open Cluster', '~O~')
	
	def __init__(self, id, symbol):
		self.id = id
		self.symbol = symbol
	
	@staticmethod
	def fromStr(name: str) -> StellarType:
		name = name.lower()  # Ignore Case
		for tp in list(StellarType):
			if tp.id.lower() == name:
				return tp
		
		raise ValueError("No Stellar Type with identifier '%s'" % name)

class Stellar(NamedMixin):
	"""
	A Celestial Object with location (Right Ascension & Declination), magnitude, and other parameters
	
	Attributes:
		name : str -- Name of Object
		type : StellarType -- Type of Stellar Object
		constell : str -- Name of Constellation the Object is in
		aliases : [str] -- List of other names for Object
		
		dist : float -- Distance of the Object in light-years
		point : SpherePoint -- Location of star on celestial sphere
		
		appmag : float -- Apparent magnitude of the Object
		absmag : float -- Absolute magnitude of the Object
		
		right_asc_motion : float -- Rate of apparent motion longitudinally in milliarcseconds per year
		decl_motion : float -- Rate of apparent motion latitudinally in milliarcseconds per year
		radial_motion : float -- Rate of approach or departure in kilometers per second
	"""
	
	
	@fromXML('name', '@name', required=True)
	@fromXML('type', '@type', parser=StellarType.fromStr, default=StellarType.STAR)
	@fromXML('right_asc', 'location/@right-asc', required=True, parser=lambda s: Angle(s, isdeg=True))
	@fromXML('decl', 'location/@decl', required=True, parser=lambda s: Angle(s, isdeg=True))
	
	@fromXML('constell', '@constellation')
	@fromXML('aliases', 'alias', multiple=True)
	
	@fromXML('dist', 'location/@distance', parser=float)
	@fromXML('appmag', 'magnitude/@apparent', parser=float)
	@fromXML('absmag', 'magnitude/@absolute', parser=float)
	
	@fromXML('right_asc_motion', 'motion/@right-asc', parser=float)
	@fromXML('decl_motion', 'motion/@decl', parser=float)
	@fromXML('radial_motion', 'motion/@radial', parser=float)
	def __init__(self, **prms):
		# Convert prms into namespace-like object
		prms = type('', (), prms)()
		
		# Initialize name and aliases
		self.initNames(prms.name, prms.aliases)
		self.constell = prms.constell
		
		# Set symbol according to type and apparent magnitude
		self.__createSymbol(prms.type, prms.appmag)
			
		# Convert ra and dec to degrees and create SpherePoint
		self.point = SpherePoint(prms.decl, prms.right_asc)
		self.dist = prms.dist
		
		# Set magnitudes
		self.appmag = prms.appmag
		self.absmag = prms.absmag
		
		# Set motions
		self.right_asc_motion = prms.right_asc_motion
		self.decl_motion = prms.decl_motion
		self.radial_motion = prms.radial_motion
		
	def __createSymbol(self, tp: StellarType, appmag: float) -> None:
		"""
		Produce string used to represent this Object in the window
		
		Output:
			appmag < 0        -->  {@}
			0 <= appmag < 1   -->  (#)
			1 <= appmag < 2   -->  (*)
			2 <= appmag < 3   -->  (")
			3 <= appmag < 4   -->   #
			4 <= appmag < 5   -->   *
			5 <= appmag < 6   -->   "
			6 <= appmag       -->   `
		"""
		
		if tp == StellarType.STAR:
			# For stars use scale
			
			if appmag is None or appmag >= 6 :  # Upper Bound
				# Default to dimmest marker
				self.symbol = '`'
			elif appmag < 0 :  # Lower Bound
				self.symbol = '{@}'
			else:
				self.symbol = ['(#)', '(*)', '(")', '#', '*', '"'][int(appmag)]
		else:
			# For other objects use type symbol
			self.symbol = tp.symbol
	
	
	def __str__(self, fields: List[str] = None, observer: Observer = None) -> str:
		"""
		Create info string for this Stellar object
		
		Args:
			fields : [str] -- List of field names that should be included
			    in the info. These include the fields of Stellar, as well as
			    'altaz' if the Altitude & Azimuth should be found and
				'point' if Right Ascension & Declination should be shown
			    NOTE: If None then all fields are provided
			observer : Observer -- Object containing the time, location, and body to view from
			    NOTE: Must be given to get Altitude & Azimuth (altaz) or RA & Dec (point)
		
		Returns:
			str -- Informational String
		"""
		
		# Ignore case on fields
		if fields is not None:
			fields = {f.lower() for f in fields}
		
		def doField(f):
			""" Check whether a field should be printed """
			return (fields is None or f in fields) and hasattr(self, f) and getattr(self, f) is not None
		
		# Accumulate string
		info = self.name  # Show name
		# Show constellation name
		if doField('constell'):
			info += '    (' + self.constell + ')'
		info += '\n'
		
		if doField('aliases'):  # Print Other Names
			info += '  |  '.join(self.aliases) + '\n'
		
		# Print Altitude & Azimuth if toView transform is provided
		if doField('altaz') and observer is not None:
			pt = observer.toHoriz(self.point)  # Get location in horizontal coordinates
			info += "(Alt, Az):  %fd ,  %fd" % (pt.latd, (-pt.longd) % 360) + '\n'  # Altitude & Azimuth in degrees
		
		if doField('point'):  # Print Right Ascension and Declination
			# Right Ascension & Declination
			info += "(RA, Dec):  %s ,  %s" % (self.point.longAng.hmsstr, self.point.latAng.dmsstr) + '\n'
		
		# Show Magnitudes
		isMag = False  # If at least one of the magnitudes is shown
		if doField('appmag'):
			info += "App Mag: %g    " % self.appmag
			isMag = True
		if doField('absmag'):
			info += "Abs Mag: %g" % self.absmag
			isMag = True
		info += '\n' if isMag else ''
		
		# Show Distance
		if doField('dist'):
			info += "Distance: %s ly\n" % self.dist
		
		# Show Motions
		if doField('radial_motion'):
			info += "Radial Motion: %f km/s\n" % self.radial_motion
			
		if doField('right_asc_motion') and doField('decl_motion'):
			info += "Proper Motion (RA, Dec): %f mas/yr,  %f mas/yr\n" % (self.right_asc_motion, self.decl_motion)
		
		return info





class Catalog:
	"""
	Store a set of Body and Stellar Objects
	
	Attributes:
		bodies : [Body] -- List of Body objects in Solar System
		stellars : [Stellar] -- List of Stellar objects outside Solar System
	"""
	
	def __init__(self, bodies: [Body] = None, stellars: [Stellar] = None):
		if bodies is None:
			self.bodies = []
		else:
			self.bodies = bodies
		
		if stellars is None:
			self.stellars = []
		else:
			self.stellars = stellars
	
	def __iter__(self):
		return iter(self.bodies + self.stellars)
	
	def __len__(self) -> int:
		return len(self.bodies) + len(self.stellars)
	
	def __getitem__(self, key: str) -> Union[Body, Stellar]:
		""" Get Stellar Object with name or alias `key` """
		
		# Search for key among combined list
		for obj in self.bodies + self.stellars:
			if key in obj:
				return obj
		
		raise KeyError("No Object with name or alias '%s' found" % key)
	
	def __delitem__(self, key: str) -> None:
		""" Delete Stellar object with name or alias `key` if present """
		
		# Track whether any objects matching key were found
		foundAny = False
		
		# Search list of bodies for key
		for i in reversed(range(len(self.bodies))):
			if key in self.bodies[i]:
				del self.bodies[i]  # Delete object at index if present
				foundAny = True
		
		# Search list of stellars for key
		for i in reversed(range(len(self.stellars))):
			if key in self.stellars[i]:
				del self.stellars[i]
				foundAny = True
		
		if not foundAny:
			raise KeyError("No Object with name or alias '%s' found" % key)
	
	def __contains__(self, key: str) -> bool:
		""" Check if any object has name or alias `key` """
		return any(key in bd for bd in self.bodies) or any(key in st for st in self.stellars)
	
	
	def append(self, obj: Union[Body, Stellar]) -> None:
		"""
		Add Stellar object to Catalog overwriting previous object
		
		Returns:
			bool -- True if `obj` overwrote another object, False if `obj` didn't
		"""
		
		if isinstance(obj, Body):
			lst = self.bodies
		elif isinstance(obj, Stellar):
			lst = self.stellars
		else:
			raise TypeError("Only Bodys or Stellars can be append to the catalog")
		
		try:
			# Try to delete any previous elements that overlapped
			del self[obj.name]
			didOverwrite = True
		except KeyError:
			# Ignore if there aren't any
			didOverwrite = False
		
		# Add to appropriate list
		lst.append(obj)
		
		return didOverwrite
	
	
	
	def getBody(self, key: str) -> Body:
		# Look for Body object in catalog
		for bd in self.bodies:
			if key in bd:
				return bd
		
		raise KeyError("No Body named '%s' found" % key)
	
	def load(self, source: str) -> None:
		"""
		Load list of objects from given xml file and
		adds them to `self.bodies` and `self.stellars`
		
		Args:
			source : str -- Name of XML file to read
		"""
		
		tree = xml.parse(source)
		root = tree.getroot()
		
		if root.tag != 'catalog' :  # Check type of root element
			raise ValueError("Root of Catalog XML must be <catalog> ... </catalog>")
		
		for child in root :
			# Parse star elements
			if child.tag == 'stellar':
				self.append(Stellar(xml=child))
			elif child.tag == 'body':
				self.append(Body(xml=child, getBody=self.getBody))
			else:
				raise ValueError("Unknown tag '%s' found in catalog file '%s'" % (child.tag, source))


