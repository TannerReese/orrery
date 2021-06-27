import math
from datetime import datetime
from typing import Union, Tuple

from sphere import SpherePoint, Rotation
from objects import Body, Stellar

from typing import List

Vector = Tuple[float, float, float]  # Three dimensional real vector


class Observer:
	"""
	Store the state of an observer
	
	To send points in the viewing port to a rectangular window, a local mercator projection is used
	
	Attributes:
	    __view : Rotation -- Transformation from horizontal coordinates to the viewers perspective
	    width : float -- Width (in radians) of the viewing port
	    height : float -- Height (in radians) of the viewing port
	    
		__body : Body -- Body from which observations are being made
	    __time : datetime.datetime -- Date and time of observation
	    __loc : SpherePoint -- Location on Earth's surface of observation
		__offset : datetime.timedelta -- Offset of `__time` from actual time
		    If not None then `time` will move forward normally otherwise it is static
		
		__toView : Rotation -- Transformation from reference coordinates to viewer perspective
	    
	    __byX : [(float, Stellar)] -- List of objects visible in window ordered by x-value. First element of tuple is x-value
	    __byY : [(float, Stellar)] -- List of objects visible in window ordered by y-value. First element of tuple is y-value
	    selected : Stellar -- Reference to currently selected object
	
	Properties:
		toView : Rotation -- Return __toView or calculate if necessary
		toHoriz : Rotation -- Transformation from reference frame to horizontal coordinates
	    time : datetime.datetime -- Get private date and time
	    location : SpherePoint -- Get private location
		position : Vector -- Position of this observer on their body in the reference coordinates
	"""
	
	def __init__(self,
		time: datetime, loc: SpherePoint, body: Body,
		wid: float = math.radians(50), hei: float = math.radians(50),
		sync: bool = False
	):
		self.__view = Rotation.identity()
		self.width = wid
		self.height = hei
		
		# Defer calculation for when it is needed
		self.__toView = None
		
		self.__body = body
		self.__time = time
		self.__loc = loc
		
		if sync:
			self.__offset = time - datetime.utcnow()
		else:
			self.__offset = None
		
		# Initialize selection system
		self.__byX, self.__byY = [], []
		self.selected = None
	
	
	
	def lookUp(self, angle: float) -> None:
		"""
		Move view upwards by `angle` (in radians) from the perspective of the observer
		Negative values of `angle` move down
		"""
		self.__view = Rotation(0, 1, 0, angle) * self.__view
		self.__toView = None  # Mark __toView for recalculation
	
	def lookRight(self, angle: float) -> None:
		"""
		Move view rightwards by `angle` (in radians) from the perspective of the observer
		Negative values of `angle` move left
		"""
		self.__view = Rotation(0, 0, 1, angle) * self.__view
		self.__toView = None  # Mark __toView for recalculation
	
	def lookClock(self, angle: float) -> None:
		"""
		Rotate the view by `angle` (in radians) clockwise from the perspective of the observer
		Causes an apparent clockwise rotation of while maintaining the center of the view
		Negative values of `angle` rotate counter-clockwise
		"""
		self.__view = Rotation(-1, 0, 0, angle) * self.__view
		self.__toView = None  # Mark __toView for recalculation
	
	def lookTo(self, point: SpherePoint, prop: float = 1) -> None:
		"""
		Move view so that the center of the view points to `point`
		Note: `point` is in horizontal coordinates
		
		Args:
			point : SpherePoint -- point to look at
			prop : float -- how much of the way to `point` the rotation goes
		"""
		# Calculate apparent position
		appar = self.__view(point)
		# Move into center of view
		self.__view = Rotation.moveTo(appar, SpherePoint(0, 0), prop) * self.__view
		self.__toView = None  # Mark __toView for recalculation
	
	
	
	# Methods for Selection System
	
	def selectBy(self, shift: int, isByX: bool):
		"""
		Select different element in __byline or __bycolm, moving selection
		
		Args:
		    shift : int -- Amount by which to shift selection in __byX or __byY, +1 corresponds to the next element
		    isByX : bool -- Whether __byline should be used or __bycolm
		"""
		
		# Get list to use for shifting
		if isByX:
			lst = self.__byX
		else:
			lst = self.__byY
		
		try:
			# Find selected object
			ind = [x for _, x in lst].index(self.selected)
			# Shift index
			ind += shift
		except ValueError:  # If selected object isn't in list choose defaults
			if shift >= 0 :
				ind = 0  # When shift is positive moves forward select the first
			else:
				ind = -1  # When shift is negative moves backward select the last
		
		# Set new selection
		if len(lst) == 0:
			self.selected = None  # When no object to select
		else:
			self.selected = lst[ind % len(lst)][1]
	
	
	def __addVisible(self, obj: Union[Body, Stellar], x: float, y: float):
		"""
		Add new visible object into __byX and __byY
		
		Args:
		    obj : Union[Body, Stellar] -- Object to add to lists
			x : int -- X-value of obj in window
			y : int -- Y-value of obj in window
		"""
		
		# Find index in self.__byX to put obj
		ind = 0
		for x1, _ in self.__byX:
			if x1 >= x:
				break
			ind += 1
		
		# Insert element at index
		self.__byX.insert(ind, (x, obj))
		
		# Find index in self.__bycolm to put obj
		ind = 0
		for y1, _ in self.__byY:
			if y1 >= y:
				break
			ind += 1
		
		# Insert element at index
		self.__byY.insert(ind, (y, obj))
	
	def clearVisible(self):
		"""
		Clear lists of visible objects
		"""
		
		self.__byX = []
		self.__byY = []
	
	
	def toRef(self, obj: Union[Body, Stellar]) -> SpherePoint:
		"""
		Find the apparent reference coordinates
		of an object to this observer
		
		Args:
			obj : Body or Stellar -- Object to locate
		
		Returns:
			SpherePoint -- Apparent position of object in reference frame
		"""
		
		if isinstance(obj, Body):
			# Do not show own body
			if obj == self.__body:
				return None
			
			# Get location of body
			(x, y, z) = obj.position(self.__time)
			# Get own position
			(sx, sy, sz) = self.position
			
			# Find difference between positions
			return SpherePoint(x - sx, y - sy, z - sz)
			
		elif isinstance(obj, Stellar):
			return obj.point
		else:
			raise TypeError("Only Body or Stellar can be converted to reference coordinates")
	
	@property
	def toHoriz(self) -> Rotation:
		return self.__body.rotator(self.__time, self.__loc)
	
	@property
	def toView(self) -> Rotation:
		if self.__toView is None:
			# Reclaculate toView transform if invalidated
			
			# Get transform to horizontal coordinates
			self.__toView = self.__body.rotator(self.__time, self.__loc)
			
			# Apply transform to get to viewer perspective
			self.__toView = self.__view * self.__toView
		
		return self.__toView
	
	def updateTime(self) -> None:
		"""
		Update the `__time` if this observer is moving forward in time
		"""
		
		if self.__offset is not None:
			self.time = self.__offset + datetime.utcnow()
	
	@property
	def time(self) -> datetime:
		return self.__time
	
	@time.setter
	def time(self, tm: datetime) -> None:
		self.__time = tm
		self.__toView = None  # Invalidate transform
	
	@property
	def location(self) -> SpherePoint:
		return self.__loc
	
	@property
	def position(self) -> Vector:
		return self.__body.position(self.__time)
	
	@property
	def center(self) -> SpherePoint:
		"""
		Get the SpherePoint in horizontal coordinates
		which corresponds to the center of the viewport
		"""
		return self.__view.inverse(SpherePoint(0, 0))
	
	
	
	def horizToWindow(self, pt: SpherePoint) -> (float, float):
		"""
		Convert point `pt` in horizontal coordinates to xy-coordinate in window
		
		Args:
		    pt : SpherePoint -- Location in horizontal coordinates to get xy-coordinate in window for
		
		Returns:
		    (float, float)  -- x-value and y-value in window for given point
		        Both x and y range from 0 to 1 when inside window
		"""
		
		# Transform point into viewer's coordinates
		point = self.__view(pt)
		
		# Convert to rectangular coordinates in window
		return (0.5 - point.long / self.width, 0.5 - point.lat / self.height)
	
	def objToWindow(self, obj: Union[Body, Stellar]) -> (float, float):
		"""
		Takes `obj` and finds its xy-coordinates in the window
		And adds `obj` to the list of visible objects if it is visible
		
		Args:
			obj : Body or Stellar -- Object to get window coordinates of
		
		Returns:
			(float, float) -- x-value and y-value in window for given stellar object
			    Both x and y range from 0 to 1 when inside window
		"""
		
		# Get point in reference coordinates
		point = self.toRef(obj)
		if point is None:
			# Don't draw element if no point given
			return (-1, -1)
		
		# Transform point into viewer's coordinates
		point = self.toView(point)
		
		# Convert to rectangular coordinates in window
		x, y = 0.5 - point.long / self.width, 0.5 - point.lat / self.height
		
		if 0 <= x < 1 and 0 <= y < 1 :
			# Add to lists of visible objects if visible
			self.__addVisible(obj, x, y)
		
		return x, y


