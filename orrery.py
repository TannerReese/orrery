#!/usr/bin/env python3

import curses
import curses.ascii
import datetime as dt
import sys
import os
import argparse

from celestial import *

from typing import List



def loadCatalog(catalog_paths):
	# Create catalog object
	catalog = Catalog()
	
	# Try to parse requested catalogs
	for path in catalog_paths :
		try:
			catalog.load(path)
		except FileNotFoundError:
			print(f"Warning: Could not find catalog file '{path}'", file=sys.stderr)
		except ValueError:
			print(f"Warning: Catalog file '{path}' may contain invalid values", file=sys.stderr)
	
	# Check user's home folder for catalogs
	paths = []
	try:
		userhome = os.path.expanduser('~/.orrery')
		paths += filter(lambda path: path.endswith('.xml'), os.listdir(userhome))
	except FileNotFoundError:
		pass
	
	# Check application info for default catalog
	paths.append('/usr/share/orrery/catalog.xml') 
	paths.append('/usr/local/share/orrery/catalog.xml') 
	
	# Check paths
	for p in paths:
		try:
			catalog.load(p)
		except FileNotFoundError:
			pass
	
	# Check that catalog contains some objects
	if len(catalog) == 0 :
		print(f"Error: No Object Information loaded in catalog file ; Try adding '-i' option", file=sys.stderr)
		exit(1)
	
	return catalog



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
	
	# win.addstr will error if a character is attempted to be drawn to the lower right hand corner
	height, width = height - 1, width - 1
	
	# Move starting column to accomodate symbol
	x -= len(text) // 2
	# Print each character in text
	isvis = False  # Track if any characters are visible
	for i in range(len(text)) :
		if 0 <= x + i < width and 0 <= y < height :
			# curses.window.addch had a bug preventing the use of color
			# curses.window.addstr had to be used to allow use of color
			try:
				win.addstr(y, x + i, text[i], attr)
			except:
				curses.endwin()
				print(y, x, text[i], i, attr, height, width)
				exit()
			
			isvis = True
	
	return isvis



# Cardinal directions with Labels for `render` method
# (SpherePoint in horizontal coordinates, Name)
CARDINALS = [
	(SpherePoint(0, 0), 'North'), (SpherePoint(0, math.pi), 'South'),
	(SpherePoint(0, -math.pi / 2), 'East'), (SpherePoint(0, math.pi / 2), 'West'),
	(SpherePoint(math.pi / 2, 0), 'Zenith'), (SpherePoint(-math.pi / 2, 0), 'Nadir'),
	(SpherePoint(0, -math.pi / 4), 'NE'), (SpherePoint(0, 3 * math.pi / 4), 'SW'),
	(SpherePoint(0, math.pi / 4), 'NW'), (SpherePoint(0, -3 * math.pi / 4), 'SE')
]

def render(catalog: List[Stellar], win: 'curses.window', celes: Celestial, doCardinals: bool = True):
	"""
	Draws all stars in given catalog as well as the labels for directions
	
	Args:
		catalog : [Stellar] -- List of objects to draw to screen
		win : ncurses.window -- Curses Window to Draw to
		celes : Celestial -- Observation Viewpoint to use to locate objects
		doCardinals : bool -- Whether labels for cardinal directions should be drawn
	"""
	
	# Clear contents of window
	win.clear()
	# Get width and height of window
	height, width = win.getmaxyx()
	
	# Clear list of visible objects
	celes.clearVisible()
	
	# Draw Objects
	for st in catalog :
		# Get coordinates of object in window
		x, y = celes.starToWindow(st)
		# Convert to line and column in curses window
		y, x = int(y * height), int(x * width)
		
		# Check if `st` is selected
		if st is celes.selected :
			printCentered(win, y, x, st.symbol, curses.A_REVERSE)
		else:
			printCentered(win, y, x, st.symbol)
	
	# Draw directions
	if doCardinals:
		for pt, lbl in CARDINALS :
			# Get coordinates of label
			x, y = celes.horizToWindow(pt)
			# Convert to line and column in curses window
			y, x = int(y * height), int(x * width)
			
			# Draw label
			printCentered(win, y, x, lbl, curses.A_UNDERLINE)
	
	# Draw Info about selected object
	if celes.selected is not None :
		sel = celes.selected
		
		win.addstr(0, 0, f"{sel.name}      {sel.constell}")  # Name & Constellation
		win.addstr(1, 0, "  |  ".join(sel.aliases))  # Print other names
		
		pt = celes.sky(sel.point)  # Get location in horizontal coordinates
		win.addstr(2, 0, f"(Alt, Az):  {pt.latd}d ,  {(-pt.longd) % 360}d")  # Altitude & Azimuth in degrees
		rah, ram, ras = sel.right_asc  # Get Hours, Minutes, and Seconds of Right Ascension
		dcd, dcm, dcs = sel.decl  # Get Degrees, Minutes, and Seconds of Declination
		dcsign = '-' if dcd < 0 else '+'  # Get sign of declination
		dcd, dcm, dcs = abs(dcd), abs(dcm), abs(dcs)  # Remove sign from components
		win.addstr(3, 0, f"(RA, Dec):  {rah}h {ram}m {ras}s ,  {dcsign}{dcd}d {dcm}m {dcs}s")  # Right Ascension & Declination
	
	# Draw Info about Time, Location, and View
	rows, _ = win.getmaxyx()
	cnt = celes._view.inverse(SpherePoint(0, 0))  # Calculate center of Viewport
	win.addstr(rows - 3, 0, "Center of View (Alt, Az):  %.6fd ,  %.6fd" % (cnt.latd, (-cnt.longd) % 360))  # Center of Viewport
	win.addstr(rows - 2, 0, "Location: " + celes._loc.geoformat())  # Location
	win.addstr(rows - 1, 0, "Time: " + celes._time.isoformat())  # Time
	
	# Update Window to display new
	win.refresh()



if __name__ == '__main__':
	# Parse Command Line Arguments
	# -----------------------------------------------
	parser = argparse.ArgumentParser(prog='orrery',
		usage='orrery [-t DATETIME] [-l LAT,LONG] [-S | --sync] [-i CATALOG ...] [-w DEGREES] [-h DEGREES]',
		description="View stellar objects at different times and from different locations",
		epilog="Along with any catalog files given with '-i' orrery will also load object information from '~/.orrery/*.xml' and '/usr/share/orrery/catalog.xml'"
	)
	# Time that should be assumed for display
	parser.add_argument('-t', '--time',
		type=dt.datetime.fromisoformat, default=dt.datetime.utcnow(),
		metavar='YYYY-MM-DD[*hh[:mm][:ss[.fff]]]', dest='time',
		help="Time to observe the sky at. Defaults to Now"
	)
	parser.add_argument('-l', '--location',
		type=SpherePoint.parseLatLong, default=SpherePoint(0, 0),
		metavar='LAT,LONG', dest='loc',
		help="Latitude and Longitude (in degrees) of location to observe from. Defaults to 0N,0W"
	)
	parser.add_argument('-S', '--sync',
		action='store_true', dest='isSync',
		help="Application will move time forward"
	)
	parser.add_argument('-i', '--input',
		type=str, nargs='+', default=[],
		metavar='CATALOG', dest='catalogs',
		help="XML file containing stellar object information formatted according to 'catalog.xsd'"
	)
	parser.add_argument('-W', '--width',
		type=int, default=50,
		metavar='DEGREES', dest='wid',
		help="Angular width in degrees of the viewport"
	)
	parser.add_argument('-H', '--height',
		type=int, default=50,
		metavar='DEGREES', dest='hei',
		help="Angular height in degrees of the viewport"
	)
	
	subparsers = parser.add_subparsers(title="subcommands", metavar='', dest='cmd')
	# Subparser for showing attributes of objects
	show_parser = subparsers.add_parser('show',
		usage='orrery [-t DATETIME] [-l LAT,LONG] [-i CATALOG ...] show [-Cnrmdv | -a] <object> ...',
		description="Show the attributes of objects",
		help="Show the attributes of objects"
	)
	show_parser.add_argument('objects',
		nargs='+',
		help="Objects to display attributes for"
	)
	show_parser.add_argument('-C', '--constellation',
		action='store_true', dest='showConstell',
		help="Show the Constellation the Object(s) are in"
	)
	show_parser.add_argument('-n', '--aliases',
		action='store_true', dest='showAliases',
		help="Show the other names of the Object(s)"
	)
	show_parser.add_argument('-r', '--radec',
		action='store_true', dest='showRADec',
		help="Show the Right Ascension and Declination"
	)
	show_parser.add_argument('-m', '--magnitude',
		action='store_true', dest='showMag',
		help="Show Apparent and Absolute Magnitude"
	)
	show_parser.add_argument('-d', '--distance',
		action='store_true', dest='showDist',
		help="Show Distance to object"
	)
	show_parser.add_argument('-v', '--velocity',
		action='store_true', dest='showMotion',
		help="Show Radial Velocity as well as rate of change of Right Ascension and Declination"
	)
	show_parser.add_argument('-a', '--all',
		action='store_true', dest='showAll',
		help="Show all available attributes of the object"
	)
	
	args = parser.parse_args()  # Get argument namespace
	
	
	# Construct Celestial Sphere
	celes = Celestial(args.time, args.loc, math.radians(args.wid), math.radians(args.hei))
	
	# Load Stellar Catalog(s)
	# -----------------------
	catalog = loadCatalog(args.catalogs)
	
	
	# Check for subcommand
	if 'cmd' in args :
		if args.cmd == 'show' :  # 'show' command
			if args.showAll :  # Show all when `showAll`
				args.showConstell = True
				args.showAliases = True
				args.showRADec = True
				args.showMag = True
				args.showDist = True
				args.showMotion = True
			
			# Iterate through chosen objects
			for name in args.objects :
				st = findInCatalog(catalog, name)
				if st is None :
					print(f"Error: Could not find object '{name}' in catalog", file=sys.stderr)
					print()
					continue  # Go to next object
				
				# Print properties of object
				print(st.name, end='  ')  # Print Name
				if args.showConstell :  # Print Constellation
					print('(' + st.constell + ')')
				else:
					print()
				
				if args.showAliases :  # Print Other Names
					print('  |  '.join(st.aliases))
				
				# Print Altitude & Azimuth
				pt = celes.sky(st.point)  # Get location in horizontal coordinates
				print(f"(Alt, Az):  {pt.latd}d ,  {(-pt.longd) % 360}d")  # Altitude & Azimuth in degrees
				
				if args.showRADec :  # Print Right Ascension and Declination
					rah, ram, ras = st.right_asc  # Get Hours, Minutes, and Seconds of Right Ascension
					dcd, dcm, dcs = st.decl  # Get Degrees, Minutes, and Seconds of Declination
					dcsign = '-' if dcd < 0 else '+'  # Get sign of declination
					dcd, dcm, dcs = abs(dcd), abs(dcm), abs(dcs)  # Remove sign from components
					print(f"(RA, Dec):  {rah}h {ram}m {ras}s ,  {dcsign}{dcd}d {dcm}m {dcs}s")  # Right Ascension & Declination
				
				if args.showMag and st.appmag is not None :  # Print Apparent Magnitude
					print(f"App Mag:", st.appmag)
				
				if args.showMag and st.absmag is not None :  # Print Absolute Magnitude
					print("Abs Mag:", st.absmag)
				
				if args.showDist :  # Print Distance
					print(f"Distance:", st.dist, "ly")
				
				if args.showMotion :  # Print Motion
					print(f"Radial Motion: {st.radial_motion} km/s", end="     ")
					print(f"Proper Motion (RA, Dec): {st.proper_motion[0]} mas/yr,  {st.proper_motion[1]} mas/yr")
				
				print()  # Newline before next object
			
			exit()  # Leave and don't call ncurses
	
	
	
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
	
	
		
	# Render & Event Loop
	# -----------------------------------------------
	running = True
	timeOffset = args.time - dt.datetime.utcnow()  # Calculate time offset from present
	while running:
		# Update Time and Recalculate Sky transform
		if args.isSync:
			celes.time = dt.datetime.utcnow() + timeOffset
		
		# Render Objects to Window
		render(catalog, stdscr, celes)
		
		
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
			celes.selectBy(-1, isByX=False)
		elif key == ord('j') :  # Move Selection Down
			celes.selectBy(1, isByX=False)
		elif key == ord('h') :  # Move Selection Left
			celes.selectBy(-1, isByX=True)
		elif key == ord('l') :  # Move Selection Right
			celes.selectBy(1, isByX=True)
		elif key in list(map(ord, ['x', 'X', curses.ascii.ctrl('c'), curses.ascii.ctrl('z')])) :  # Quit
			running = False
	
	
	# End Curses
	# -----------------------------------------------
	curses.noraw()
	stdscr.keypad(False)
	curses.noecho()
	curses.endwin()	

