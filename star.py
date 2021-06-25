import xml.etree.ElementTree as xml
from sphere import Angle, SpherePoint, Rotation
from typing import Tuple, List

from enum import Enum, unique

from utils import fromXML, NamedMixin


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
	@fromXML('type', '@type', parser=StellarType.fromStr)
	@fromXML('right_asc', 'location/@right-asc', required=True, parser=Angle)
	@fromXML('decl', 'location/@decl', required=True, parser=Angle)
	
	@fromXML('constell', '@constellation')
	@fromXML('aliases', 'alias', multiple=True)
	
	@fromXML('dist', 'location/@distance', parser=float)
	@fromXML('appmag', 'magnitude/@apparent', parser=float)
	@fromXML('absmag', 'magnitude/@absolute', parser=float)
	
	@fromXML('right_asc_motion', 'motion/@right-asc', parser=float)
	@fromXML('decl_motion', 'motion/@decl', parser=float)
	@fromXML('radial_motion', 'motion/@radial', parser=float)
	def __init__(self,
		name: str, aliases: str,
		right_asc: Angle, decl: Angle,
		constell: str = None, type: StellarType = StellarType.STAR,
		dist: float = None,
		appmag: float = None, absmag: float = None,
		right_asc_motion: float = None, decl_motion: float = None,
		radial_motion: float = None
	):
		# Initialize name and aliases
		self.initNames(name, aliases)
		self.constell = constell
		
		# Set symbol according to type and apparent magnitude
		self.__createSymbol(type, appmag)
			
		# Convert ra and dec to degrees and create SpherePoint
		self.point = SpherePoint(decl, right_asc)
		self.dist = dist
		
		# Set magnitudes
		self.appmag = appmag
		self.absmag = absmag
		
		# Set motions
		self.right_asc_motion = right_asc_motion
		self.decl_motion = decl_motion
		self.radial_motion = radial_motion
		
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



class Catalog:
	"""
	Store a set of Stellar Objects
	
	Attributes:
		objects : [Stellar] -- List of Objects
	"""
	
	def __init__(self, objects=[]):
		self.objects = objects
	
	def __iter__(self):
		return iter(self.objects)
	
	def __len__(self):
		return len(self.objects)
	
	def __getitem__(self, key):
		""" Get Stellar Object with name or alias `key` """
		
		# Search list of objects for key
		for obj in self.objects :
			if key in obj:
				return obj
		
		raise KeyError("No Object with name or alias '%s' found" % key)
	
	def __delitem__(self, key):
		""" Delete Stellar object with name or alias `key` if present """
		
		foundAny = False  # Track whether any were found
		delMore = True  # Track if there are remaining elements to look for
		while delMore:
			delMore = False
			
			# Search list of objects for key
			for i in range(len(self.objects)) :
				obj = self.objects[i]
				if key in obj:
					del self.objects[i]  # Delete object at index if present
					foundAny, delMore = True, True
					break
		
		if not foundAny:
			raise KeyError("No Object with name or alias '%s' found" % key)
	
	def __contains__(self, key):
		""" Check if any object has name or alias `key` """
		return any(map(lambda obj: key in obj, self.objects))
	
	
	def append(self, obj: Stellar):
		"""
		Add Stellar object to Catalog overwriting previous object
		
		Returns:
			bool -- True if `obj` overwrote another object, False if `obj` didn't
		"""
		
		try:
			# Try to delete any previous elements that overlapped
			del self[obj.name]
			didOverwrite = True
		except KeyError:
			# Ignore if there aren't any
			didOverwrite = False
		
		self.objects.append(obj)
		return didOverwrite
	
	
	def load(self, source: str):
		"""
		Load list of objects from given xml file and adds them to `self.objects`
		
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


