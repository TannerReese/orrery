import xml.etree.ElementTree as xml
from sphere import *
from typing import Tuple, List

from utils import *


class Stellar:
	"""
	A Celestial Object with location (Right Ascension & Declination), magnitude, and other parameters
	
	Attributes:
		name : str -- Name of Object
		constell : str -- Name of Constellation the Object is in
		aliases : [str] -- List of other names for Object
		
	    right_asc : (int, int, float) -- Right Ascension represented as triple of (Hours, Minutes, Seconds)
		decl : (int, int, float) -- Declination represented as triple of (Degrees, Minutes, Seconds)
		dist : float -- Distance of the Object in light-years
		point : SpherePoint -- Location of star on celestial sphere
		
		appmag : float -- Apparent magnitude of the Object
		absmag : float -- Absolute magnitude of the Object
		
		right_asc_motion : float -- Rate of apparent motion longitudinally in milliarcseconds per year
		decl_motion : float -- Rate of apparent motion latitudinally in milliarcseconds per year
		radial_motion : float -- Rate of approach or departure in kilometers per second
	"""
	
	
	@fromXML('name', '@name', required=True)
	@fromXML('right_asc', 'location/@right-asc', required=True, parser=lambda s: parseAngle(s, isdms=False))
	@fromXML('decl', 'location/@decl', required=True, parser=lambda s: parseAngle(s, isdms=True))
	
	@fromXML('constell', '@constellation')
	@fromXML('aliases', 'alias', multiple=True)
	
	@fromXML('dist', 'location/@distance', parser=float)
	@fromXML('appmag', 'magnitude/@apparent', parser=float)
	@fromXML('absmag', 'magnitude/@absolute', parser=float)
	
	@fromXML('right_asc_motion', 'motion/@right-asc', parser=float)
	@fromXML('decl_motion', 'motion/@decl', parser=float)
	@fromXML('radial_motion', 'motion/@radial', parser=float)
	def __init__(self, **kwargs):
		# Set attributes obtained from XML
		for key, value in kwargs.items():
			setattr(self, key, value)
		
		# Convert ra and dec to degrees and create SpherePoint
		self.point = SpherePoint(
			self.decl[0] + (self.decl[1] + self.decl[2] / 60) / 60,
			(self.right_asc[0] + (self.right_asc[1] + self.right_asc[2] / 60) / 60) * 15,
		isdeg=True)
	
	@property
	def symbol(self):
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
		
		if self.appmag < 0 :  # Lower Bound
			return '{@}'
		elif self.appmag >= 6 :  # Upper Bound
			return '`'
		else:
			return ['(#)', '(*)', '(")', '#', '*', '"'][int(self.appmag)]



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
		
		# Ignore key's case
		key = key.lower()
		
		# Search list of objects for key
		for st in self.objects :
			if key == st.name.lower() or key in map(lambda a: a.lower(), st.aliases) :
				return st
		
		raise IndexError(f"No Object with name or alias '{key}' found")
	
	def __delitem__(self, key):
		""" Delete Stellar object with name or alias `key` if present """
		
		# Ignore key's case
		key = key.lower()
		
		# Search list of objects for key
		for i in range(len(self.objects)) :
			st = self.objects[i]
			if key == st.name.lower() or key in map(lambda a: a.lower(), st.aliases) :
				del self.objects[i]  # Delete object at index if present
				return
		
		raise IndexError(f"No Object with name or alias '{key}' found")
	
	def __contains__(self, key):
		""" Check if any object has name or alias `key` """
		key = key.lower()  # Ignore key's case
		return any(map(lambda st: key == st.name.lower() or key in map(lambda a: a.lower(), st.aliases), self.objects))
	
	
	def append(self, st: Stellar):
		"""
		Add Stellar object to Catalog if not already present
		
		Returns:
		    bool -- True if `st` was added, False if `st` was already present
		"""
		
		if self.__contains__(st.name) :
			return False
		else:
			self.objects.append(st)
			return True
	
	
	
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
			if child.tag == 'star' :
				self.append(Stellar(xml=child))


