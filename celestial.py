#!/usr/bin/env python3

import curses
import curses.ascii
import datetime as dt
import sys
import argparse

from sphere import *
from star import *

from typing import List


# Helper function to print strings to window centered on point
def printCentered(win: 'curses.window', y: int, x: int, text: str, attr: int = 0):
	"""
	Prints `text` to `win` such that its center lies at (y, x)
	Doesn't through errors when out of bounds
	
	Args:
	    win : curses.window -- Curses Window to draw to
	    y : int -- Row to write text in
	    x : int -- Column to write text in
	    text : str -- Text to write
	    attr : int = 0 -- Curses Attributes to draw text with
	
	Returns:
	    bool -- Whether the drawn text is visible
	"""
	
	# Get window dimensions
	height, width = win.getmaxyx()
	
	# Move starting column to accomodate symbol
	x -= len(text) // 2
	# Print each character in text
	isvis = False  # Track if any characters are visible
	for i in range(len(text)) :
		if 0 <= x + i < width and 0 <= y < height :
			# curses.window.addch had a bug preventing the use of color
			# curses.window.addstr had to be used to allow use of color
			win.addstr(y, x + i, text[i], attr)
			
			isvis = True
	
	return isvis


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
	    
	    _byline : [(int, Stellar)] -- List of objects visible in window ordered by which line they are on. First element of tuple is line number
	    _bycolm : [(int, Stellar)] -- List of objects visible in window ordered by which column they are on. First element of tuple is column number
	    _selected : Stellar -- Reference to currently selected object
	
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
		self._byline, self._bycolm = [], []
		self._selected = None
	
	
	
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
	
	def selectBy(self, shift: int, isByLine: bool):
		"""
		Select different element in _byline or _bycolm, moving selection
		
		Args:
		    shift : int -- Amount by which to shift selection in _byline, +1 corresponds to the next element
		    isByLine : bool -- Whether _byline should be used or _bycolm
		"""
		
		# Get list to use for shifting
		if isByLine:
			lst = self._byline
		else:
			lst = self._bycolm
		
		try:
			# Find selected object
			ind = list(map(lambda x: x[1], lst)).index(self._selected)
			# Shift index
			ind += shift
		except ValueError:  # If _selected object isn't in list choose defaults
			if shift >= 0 :
				ind = 0  # When shift is moves forward select the first
			else:
				ind = -1  # When shift moves backward select the last
		
		# Set new selection
		if len(lst) == 0 :
			self._selected = None  # When no object to select
		else:
			self._selected = lst[ind % len(lst)][1]
	
	def _addVisible(self, obj: Stellar, line: int, colm: int):
		"""
		Add new visible object into _byline and _bycolm
		
		Args:
		    obj : Stellar -- Object to add to lists
			line : int -- Line that obj is on in window
			colm : int -- Column that obj is on in window
		"""
		
		# Find index in self._byline to put obj
		ind = 0
		for ln, _ in self._byline :
			if ln >= line:
				break
			ind += 1
		
		# Insert element at index
		self._byline.insert(ind, (line, obj))
		
		# Find index in self._bycolm to put obj
		ind = 0
		for cl, _ in self._bycolm :
			if cl >= colm:
				break
			ind += 1
		
		# Insert element at index
		self._bycolm.insert(ind, (colm, obj))
	
	
	
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
	
	
	
	def drawHoriz(self, win: 'curses.window', pt: SpherePoint, text: str, attr: int = None) -> None:
		"""
		Draws `text` on curses window `win` assuming `pt` is in horizontal coordinates
		
		Args:
			win : curses.window -- Window to draw string to
			pt : SpherePoint -- Location in horizontal coordinates to draw string
			text : str -- String to draw
			attr : int -- Curses Attributes used to draw text
		"""
		
		# Transform point into viewer's coordinates
		point = self._view(pt)
		
		# Convert to rectangular coordinates for curses window
		height, width = win.getmaxyx()
		x = int((0.5 - point.long / self.width) * width)
		y = int((0.5 - point.lat / self.height) * height)
		
		# Print symbol centered at (y, x)
		printCentered(win, y, x, text, attr)
	
	def draw(self, win: 'curses.window', star: Stellar, attr: int = 0) -> None:
		"""
		Takes `star` and draws it on the curses window `win`
		Location of star is assumed to be in equatorial coordinates
		
		Args:
			win : curses.window -- Window to draw resulting object to
			star : Stellar -- Stellar containing location and magnitude information
			attr : int = 0 -- Curses Attributed used to draw `star`
		"""
		
		# Transform point into viewer's coordinates
		point = self.total(star.point)
		
		# Convert to rectangular coordinates for curses window
		height, width = win.getmaxyx()
		x = int((0.5 - point.long / self.width) * width)
		y = int((0.5 - point.lat / self.height) * height)
		
		# Print symbol centered at (y, x)
		if printCentered(win, y, x, star.symbol, attr):
			# Add to lists of visible objects if visible
			self._addVisible(star, y, x)
	
	
	# Cardinal directions with Labels for `render` method
	# (SpherePoint in horizontal coordinates, Name)
	CARDINALS = [
		(SpherePoint(0, 0), 'North'), (SpherePoint(0, math.pi), 'South'),
		(SpherePoint(0, -math.pi / 2), 'East'), (SpherePoint(0, math.pi / 2), 'West'),
		(SpherePoint(math.pi / 2, 0), 'Zenith'), (SpherePoint(-math.pi / 2, 0), 'Nadir'),
		(SpherePoint(0, -math.pi / 4), 'NE'), (SpherePoint(0, 3 * math.pi / 4), 'SW'),
		(SpherePoint(0, math.pi / 4), 'NW'), (SpherePoint(0, -3 * math.pi / 4), 'SE')
	]
	
	def render(self, win: 'curses.window', catalog: List[Stellar], doCardinals: bool = True):
		"""
		Draws all stars in given catalog as well as the labels for directions
		
		Args:
		    win : ncurses.window -- Curses Window to Draw to
		    catalog : [Stellar] -- List of objects to draw to screen
		    doCardinals : bool -- Whether labels for cardinal directions should be drawn
		"""
		
		# Clear contents of window
		win.clear()
		# Clear list of visible objects
		self._byline, self._bycolm = [], []
		
		# Draw Objects
		for st in catalog :
			# Check if `st` is selected
			if st is self._selected :
				self.draw(win, st, curses.A_REVERSE)
			else:
				self.draw(win, st)
		
		# Draw directions
		if doCardinals:
			for pt, lbl in Celestial.CARDINALS :
				self.drawHoriz(win, pt, lbl, curses.A_UNDERLINE)
		
		# Draw Info about selected object
		if self._selected is not None :
			win.addstr(0, 0, f"{self._selected.name}      {self._selected.constell}")  # Name & Constellation
			win.addstr(1, 0, "  |  ".join(self._selected.aliases))  # Print other names
			
			pt = self.sky(self._selected.point)  # Get location in horizontal coordinates
			win.addstr(2, 0, f"(Alt, Az):  {pt.latd}d ,  {(-pt.longd) % 360}d")  # Altitude & Azimuth in degrees
			rah, ram, ras = self._selected.right_asc  # Get Hours, Minutes, and Seconds of Right Ascension
			dcd, dcm, dcs = self._selected.decl  # Get Degrees, Minutes, and Seconds of Declination
			dcsign = '-' if dcd < 0 else '+'  # Get sign of declination
			dcd, dcm, dcs = abs(dcd), abs(dcm), abs(dcs)  # Remove sign from components
			win.addstr(3, 0, f"(RA, Dec):  {rah}h {ram}m {ras}s ,  {dcsign}{dcd}d {dcm}m {dcs}s")  # Right Ascension & Declination
		
		# Draw Info about Time, Location, and View
		rows, _ = win.getmaxyx()
		cnt = self._view.inverse(SpherePoint(0, 0))  # Calculate center of Viewport
		win.addstr(rows - 3, 0, "Center of View (Alt, Az):  %.6fd ,  %.6fd" % (cnt.latd, (-cnt.longd) % 360))  # Center of Viewport
		win.addstr(rows - 2, 0, "Location: " + self._loc.geoformat())  # Location
		win.addstr(rows - 1, 0, "Time: " + self._time.isoformat())  # Time
		
		# Update Window to display new
		win.refresh()



if __name__ == '__main__':
	# Parse Command Line Arguments
	# -----------------------------------------------
	parser = argparse.ArgumentParser(description="")
	# Time that should be assumed for display
	parser.add_argument('-t', '--time',
		type=dt.datetime.fromisoformat,
		default=dt.datetime.utcnow(),
		metavar='DATETIME', dest='time',
		help="Time to observe the sky at. Defaults to Now"
	)
	parser.add_argument('-l', '--location',
		type=SpherePoint.parseLatLong,
		default=SpherePoint(0, 0),
		metavar='LAT,LONG', dest='loc',
		help="Latitude and Longitude (in degrees) of location to observe from. Defaults to 0N,0W"
	)
	parser.add_argument('-S', '--sync',
		action='store_true',
		dest='isSync',
		help="Application will move time forward"
	)
	parser.add_argument('-W', '--width',
		type=int,
		default=20,
		metavar='DEGREES', dest='wid',
		help="Angular width in degrees of the viewport"
	)
	parser.add_argument('-H', '--height',
		type=int,
		default=20,
		metavar='DEGREES', dest='hei',
		help="Angular height in degrees of the viewport"
	)
	
	args = parser.parse_args()  # Get argument namespace
	
	
	# Start Curses
	# -----------------------------------------------
	stdscr = curses.initscr()
	curses.noecho()  # Don't print inputted characters
	curses.curs_set(0)  # Hide cursor
	curses.raw()  # Catch control characters
	stdscr.keypad(True)   # 
	
	# Allow for color drawing
	curses.start_color()
	curses.use_default_colors()
	curses.init_pair(1, 1, -1)
	curses.init_pair(2, 2, -1)
	curses.init_pair(3, 4, -1)
	
	
	# Construct Celestial Sphere
	celes = Celestial(args.time, args.loc, math.radians(args.wid), math.radians(args.hei))
	catalog = loadCatalog('catalog.xml')  # Load Stellar Catalog
	
		
	# Render & Event Loop
	# -----------------------------------------------
	running = True
	timeOffset = args.time - dt.datetime.utcnow()  # Calculate time offset from present
	while running:
		# Update Time and Recalculate Sky transform
		if args.isSync:
			celes.time = dt.datetime.utcnow() + timeOffset
		
		# Render to Window
		celes.render(stdscr, catalog)
		
		
		# Get key events
		key = stdscr.getch()
			# Navigation Controls
		if key in [ord('w'), curses.KEY_UP] :  # Up
			celes.lookUp(celes.height / 10)
		elif key in [ord('s'), curses.KEY_DOWN] :  # Down
			celes.lookUp(-celes.height / 10)
		elif key in [ord('a'), curses.KEY_LEFT] :  # Left
			celes.lookRight(-celes.width / 10)
		elif key in [ord('d'), curses.KEY_RIGHT] :  # Right
			celes.lookRight(celes.width / 10)
		elif key == ord('q') :  # Counter-Clockwise Turn
			celes.lookClock(-0.08)
		elif key == ord('e') :  # Clockwise Turn
			celes.lookClock(0.08)
			
			# Zoom Controls
		elif key == ord('W') :  # Zoom In Vertically
			celes.height /= 1.1
		elif key == ord('S') :  # Zoom Out Vertically
			celes.height *= 1.1
		elif key == ord('A') :  # Zoom Out Horizontally
			celes.width *= 1.1
		elif key == ord('D') :  # Zoom In Horizontally
			celes.width /= 1.1
		elif key == ord('Q') :  # Zoom Out
			celes.height *= 1.1
			celes.width *= 1.1
		elif key == ord('E') :  # Zoom In
			celes.height /= 1.1
			celes.width /= 1.1
			
			# Selection Controls
		elif key == ord('k') :  # Move Selection Up
			celes.selectBy(-1, isByLine=True)
		elif key == ord('j') :  # Move Selection Down
			celes.selectBy(1, isByLine=True)
		elif key == ord('h') :  # Move Selection Left
			celes.selectBy(-1, isByLine=False)
		elif key == ord('l') :  # Move Selection Right
			celes.selectBy(1, isByLine=False)
		elif key in list(map(ord, ['x', 'X', curses.ascii.ctrl('c'), curses.ascii.ctrl('z')])) :  # Quit
			running = False
	
	
	# End Curses
	# -----------------------------------------------
	curses.noraw()
	stdscr.keypad(False)
	curses.noecho()
	curses.endwin()	

