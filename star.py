import xml.etree.ElementTree as xml
import re
from sphere import *
from typing import Tuple, List

# Compile Regular Expression for DMS / HMS angles
_angleRE = re.compile('([+-]?)([0123]?\d{1,2})([hHdD])\s*([0-5]?\d)[mM]\s*([0-5]?\d(?:\.\d+)?)[sS]', re.IGNORECASE)

def parseAngle(angstr: str, isdms: bool = False):
	""" Parse Right Ascension string in Hour Minute Second or Degree Minute Second form """
	m = _angleRE.match(angstr)
	
	# When string doesn't match
	if m is None :
		raise ValueError('String "' + angstr + '" does not match HMS or DMS format')
	
	# Check that first character is 'h' or 'H' and not 'd' or 'D'
	if m.group(3).lower() != ('d' if isdms else 'h') :
		raise ValueError('First value in HMS format must an hour')
	
	# Check for sign
	sign = m.group(1)
	if len(sign) > 0 :
		if not isdms:
			raise ValueError('HMS format is not signed')
		else:
			sign = 1 if sign == '+' else -1
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
	
	return (sign * hd, sign * m, sign * s)


def loadCatalog(source : str):
	"""
	Load list of objects from given xml file
	
	Args:
	    source : str -- Name of XML file to read
	
	Returns:
	    [Stellar] -- List of objects contained in file
	"""
	
	tree = xml.parse(source)
	root = tree.getroot()
	
	if root.tag != 'catalog' :  # Check type of root element
		raise ValueError("Root of Catalog XML must be <catalog> ... </catalog>")
	
	catalog = []  # List of stars
	for child in root :
		# Parse star elements
		if child.tag == 'star' :
			if 'name' not in child.attrib :  # Check for required name field in star
				raise ValueError("Star element must have 'name' attribute")
			else:
				name = child.attrib['name']
			
			# Get Constellation
			if 'constellation' in child.attrib :
				constell = child.attrib['constellation']
			else:
				constell = None
			
			# Get Location Parameters
			loc = child.find('location')
			if loc is None :
				raise ValueError('Star element must have a location tag')
			elif 'right-asc' not in loc.attrib or 'decl' not in loc.attrib :
				raise ValueError("Star element must have a location tag with 'right-asc' and 'decl'")
			else:
				# Parse HMS and DMS format for angle
				right_asc = parseAngle(loc.attrib['right-asc'])
				decl = parseAngle(loc.attrib['decl'], isdms=True)
				
				if 'distance' in loc.attrib :
					dist = float(loc.attrib['distance'])
					if dist < 0 :
						raise ValueError('"distance" attribute must be positive')
				else:
					dist = None
			
			# Get Magnitude Parameters
			mag = child.find('magnitude')
			if mag is not None :
				appmag, absmag = None, None
				if 'apparent' in mag.attrib :
					appmag = float(mag.attrib['apparent'])
				if 'absolute' in mag.attrib :
					absmag = float(mag.attrib['absolute'])
			
			# Get Motion Parameters
			mot = child.find('motion')
			# Set defaults
			prop_mt = [None, None]
			rad_mt = 0
			if mot is not None :
				if 'right-asc' in mot.attrib :
					prop_mt[0] = float(mot.attrib['right-asc'])
				if 'decl' in mot.attrib :
					prop_mt[1] = float(mot.attrib['decl'])
				prop_mt = tuple(prop_mt)  # Convert [right-asc, decl] to tuple
				
				if 'radial' in mot.attrib :
					rad_mt = float(mot.attrib['radial'])
			
			# Get Aliases
			aliases = map(lambda al: al.text, child.iterfind('alias'))
		
		# Construct Star
		st = Stellar(name, right_asc, decl, constell, aliases, dist, appmag, absmag, prop_mt, rad_mt)
		catalog.append(st)
	
	return catalog


def findInCatalog(catalog, name):
	""" Find Stellar object in catalog using name """
	name = name.lower()  # Ignore case
	for st in catalog :
		if name == st.name.lower() or name in map(lambda a: a.lower(), st.aliases) :
			return st
	
	return None



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
		
		proper_motion : Tuple[float, float] -- Rate of apparent motion of the Object in each direction (Right-Ascension rate, Declination rate) in milliarcseconds per year
		radial_motion : float -- Rate of approach or departure in kilometers per second
	"""
	
	
	def __init__(self,
		name: str, ra: Tuple[int, int, float], dec: Tuple[int, int, float],
		constell: str = None, aliases: List[str] = [],
		dist: float = None,
		appmag: float = None, absmag: float = None,
		prop_mt: Tuple[float, float] = (0, 0), rad_mt: float = 0
	):
		self.name = name
		self.constell = constell
		self.aliases = list(aliases)
		
		self.right_asc = ra
		self.decl = dec
		# Convert ra and dec to degrees and create SpherePoint
		self.point = SpherePoint(dec[0] + (dec[1] + dec[2] / 60) / 60, (ra[0] + (ra[1] + ra[2] / 60) / 60) * 15, isdeg=True)
		self.dist = dist
		
		# Magnitude parameters
		self.appmag = appmag
		self.absmag = absmag
		
		# Motion parameters
		self.proper_motion = prop_mt
		self.radial_motion = rad_mt
	
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

