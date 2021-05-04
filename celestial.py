import datetime as dt

from sphere import *
from star import *

from typing import List


class Celestial:
	"""
	Store the state of an observer
	
	To send points in the viewing port to a rectangular window, a local mercator projection is used
	
	Attributes:
	    _view : Rotation -- Transformation from horizontal coordinates to the viewers perspective
	    width : float -- Width (in radians) of the viewing port
	    height : float -- Height (in radians) of the viewing port
	    
		_total : Rotation -- Transformation from equatorial coordinates to viewer perspective
	    _sky : Rotation -- Store the transformation from equatorial coordinates to horizontal coordinates
	    _time : dt.datetime -- Date and time of observation
	    _loc : SpherePoint -- Location on Earth's surface of observation
	    
	    _byX : [(float, Stellar)] -- List of objects visible in window ordered by x-value. First element of tuple is x-value
	    _byY : [(float, Stellar)] -- List of objects visible in window ordered by y-value. First element of tuple is y-value
	    selected : Stellar -- Reference to currently selected object
	
	Properties:
	    sky : Rotation -- Return _sky or calculate if necessary
	    time : datetime -- Get private date and time
	    location : SpherePoint -- Get private location
	"""
	
	EPOCH_J2000 = dt.datetime(2000, 1, 1, hour=12)  # J2000 epoch on 12h, Jan 1st, 2000
	
	def __init__(self, time: dt.datetime, loc: SpherePoint, wid: float = math.radians(50), hei: float = math.radians(50)):
		self._view = Rotation.identity()
		self.width = wid
		self.height = hei
		
		self._sky = None  # Save calculation for when it is needed
		self._total = None
		
		self._time = time
		self._loc = loc
		
		# Initialize selection system
		self._byX, self._byY = [], []
		self.selected = None
	
	
	
	def lookUp(self, angle: float) -> None:
		"""
		Move view upwards by `angle` (in radians) from the perspective of the observer
		Negative values of `angle` move down
		"""
		self._view = Rotation(0, 1, 0, angle) * self._view
		self._total = None  # Mark _total for recalculation
	
	def lookRight(self, angle: float) -> None:
		"""
		Move view rightwards by `angle` (in radians) from the perspective of the observer
		Negative values of `angle` move left
		"""
		self._view = Rotation(0, 0, 1, angle) * self._view
		self._total = None  # Mark _total for recalculation
	
	def lookClock(self, angle: float) -> None:
		"""
		Rotate the view by `angle` (in radians) clockwise from the perspective of the observer
		Causes an apparent clockwise rotation of while maintaining the center of the view
		Negative values of `angle` rotate counter-clockwise
		"""
		self._view = Rotation(-1, 0, 0, angle) * self._view
		self._total = None  # Mark _total for recalculation
	
	def lookTo(self, point: SpherePoint, prop: float = 1) -> None:
		"""
		Move view so that the center of the view points to `point`
		Note: `point` is in horizontal coordinates
		
		Args:
			point : SpherePoint -- point to look at
			prop : float -- how much of the way to `point` the rotation goes
		"""
		# Calculate apparent position
		appar = self._view(point)
		# Move into center of view
		self._view = Rotation.moveTo(appar, SpherePoint(0, 0), prop) * self._view
		self._total = None  # Mark _total for recalculation
	
	
	
	# Methods for Selection System
	
	def selectBy(self, shift: int, isByX: bool):
		"""
		Select different element in _byline or _bycolm, moving selection
		
		Args:
		    shift : int -- Amount by which to shift selection in _byX or _byY, +1 corresponds to the next element
		    isByX : bool -- Whether _byline should be used or _bycolm
		"""
		
		# Get list to use for shifting
		if isByX:
			lst = self._byX
		else:
			lst = self._byY
		
		try:
			# Find selected object
			ind = list(map(lambda x: x[1], lst)).index(self.selected)
			# Shift index
			ind += shift
		except ValueError:  # If selected object isn't in list choose defaults
			if shift >= 0 :
				ind = 0  # When shift is moves forward select the first
			else:
				ind = -1  # When shift moves backward select the last
		
		# Set new selection
		if len(lst) == 0 :
			self.selected = None  # When no object to select
		else:
			self.selected = lst[ind % len(lst)][1]
	
	
	def _addVisible(self, obj: Stellar, x: float, y: float):
		"""
		Add new visible object into _byX and _byY
		
		Args:
		    obj : Stellar -- Object to add to lists
			x : int -- X-value of obj in window
			y : int -- Y-value of obj in window
		"""
		
		# Find index in self._byX to put obj
		ind = 0
		for x1, _ in self._byX :
			if x1 >= x:
				break
			ind += 1
		
		# Insert element at index
		self._byX.insert(ind, (x, obj))
		
		# Find index in self._bycolm to put obj
		ind = 0
		for y1, _ in self._byY :
			if y1 >= y:
				break
			ind += 1
		
		# Insert element at index
		self._byY.insert(ind, (y, obj))
	
	def clearVisible(self):
		"""
		Clear lists of visible objects
		"""
		
		self._byX = []
		self._byY = []
	
	
	
	@property
	def sky(self) -> Rotation:
		if self._sky is None:
			# Calculate sky transformation from _time and _loc
			
			# Calculate timedelta from epoch (J2000)
			diff = self._time - Celestial.EPOCH_J2000
			
			# ERA (Earth Rotation Angle) in radians
			days = diff.total_seconds() / 86400
			era = 2 * math.pi * (0.7790572732640 + 1.00273781191135448 * days)
			
			# GMSTp (polynomial part of Greenwhich Mean Sidereal Time) in arcseconds
			# Correction to ERA compensating for precession
			cent = days / 36525  # Number of centuries from epoch (J2000)
			gmstp = 0.014506 + 4612.156534 * cent + 1.3915817 * cent * cent
			
			# GMST in radians
			gmst = era + math.radians(gmstp / 3600)
			
			# Reorients celestial sphere for time
			tmrot = Rotation(0, 0, 1, -gmst)
			
			# Reorients sphere for location
			reloc = Rotation(0, 1, 0, math.pi / 2 - self._loc.lat) * Rotation(0, 0, 1, math.pi - self._loc.long)
			
			# Combine both corrections
			self._sky = reloc * tmrot
		
		return self._sky
	
	@property
	def total(self) -> Rotation:
		if self._total is None or self._sky is None :
			# Reclaculate total transform if necessary
			self._total = self._view * self.sky
		
		return self._total
	
	@property
	def time(self) -> dt.datetime:
		return self._time
	
	@time.setter
	def time(self, tm: dt.datetime):
		self._time = tm
		self._sky = None  # Invalidate sky transform
	
	@property
	def location(self) -> SpherePoint:
		return self._loc
	
	
	
	def horizToWindow(self, pt: SpherePoint):
		"""
		Convert point `pt` in horizontal coordinates to xy-coordinate in window
		
		Args:
		    pt : SpherePoint -- Location in horizontal coordinates to get xy-coordinate in window for
		
		Returns:
		    (float, float)  -- x-value and y-value in window for given point
		        Both x and y range from 0 to 1 when inside window
		"""
		
		# Transform point into viewer's coordinates
		point = self._view(pt)
		
		# Convert to rectangular coordinates in window
		return (0.5 - point.long / self.width, 0.5 - point.lat / self.height)
	
	def starToWindow(self, st: Stellar):
		"""
		Takes `st` and finds its xy-coordinates in the window
		And adds `st` to the list of visible objects if it is visible
		
		Args:
		    st : SpherePoint -- Stellar object to get coordinates of
		
		Returns:
		    (float, float)  -- x-value and y-value in window for given stellar object
		        Both x and y range from 0 to 1 when inside window
		"""
		
		# Transform point into viewer's coordinates
		point = self.total(st.point)
		
		# Convert to rectangular coordinates in window
		x, y = 0.5 - point.long / self.width, 0.5 - point.lat / self.height
		
		if 0 <= x < 1 and 0 <= y < 1 :
			# Add to lists of visible objects if visible
			self._addVisible(st, x, y)
		
		return x, y


