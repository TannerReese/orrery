import re

from functools import wraps
from typing import List, Callable, Any, TypeVar

Element = None

def xpath(elem: Element, path: str) -> List[str]:
	"""
	Return the contents of the nodes or attributes that are targeted by path
	
	Args:
		elem : xml.etree.ElementTree.Element -- The element that servers as the root of the XPath query
		path : str -- The XPath query string
	
	Returns:
		[str] -- List of the contents of each node or attribute found matching the path
	"""
	
	# Check for '@attribute' at end of path
	# xml.etree.ElementTree's XPath querying doesn't support targeting attributes
	if path.split('/')[-1].strip()[0] == '@':
		if '/' in path:
			idx = path.rindex('/')  # Get location of last '/' to cut at
			path, attr = path[:idx], path[idx + 1 :]
		else:
			path, attr = '', path
		
		attr = attr.strip()[1:]  # Remove whitespace and leading '@'
	else:
		attr = None
	
	# Empty path should refer to element itself
	if len(path) == 0 :
		path = '.'
	
	# Use xml.etree.ElementTree XPath querying to get elements
	targets = elem.findall(path)
	
	# Get the desired attribute if given
	results = []
	if attr is None:
		for node in targets:
			node = node.text
			
			# None is used by xml.etree.ElementTree to represent no text
			if node is None:
				node = ''
			
			results.append(node)
	else:
		results = []
		for node in targets:
			try:
				# Only add attribute if it is present
				results.append(node.attrib[attr])
			except KeyError:
				pass
	
	return results


T = TypeVar('T')
def fromXML(name: str, path: str,
		required: bool = False, multiple: bool = False,
		parser: Callable[[str], Any] = None, default: Any = None
	) -> Callable[[Callable[..., T]], Callable[[Element], T]]:
	"""
	Creates a decorator which adds an argument to parse out the given XML element.
	This decorator constructor is intended to be used to multiple times on a given function.
	Each instance adds another argument that will be extracted from the XML element and given to the function.
	If not present then either [] or `default` will be provided depending on if multiple is present.
	
	The decorated function will take an XML element as a keyword argument named `xml`
	All arguments to method besides `xml` will be passed through
	Any that overlap with those produced by `xml` will overwrite the value provided by the `xml`
	
	Usage:
		import xml.etree.ElementTree as ET
		
		@fromXML('firstName', '@name', required=True)
		@fromXML('lastName', '/@surname', required=True)
		@fromXML('paychecks', '/pay/@value', multiple=True, parser=float)
		@fromXML('isManager', '/properties/managerial', parser=bool)
		def parseEmployee(firstName, lastName, paychecks, isManager=False):
			# Combine names
			name = firstName + ' ' + lastName
			
			# Sum paychecks
			total = sum(paychecks)
			
			return Employee(name, total, isManager)
		
		parseEmployee(xml=ET.fromstring('''
			<name name="John" surname="Doe">
				<properties>
					<managerial>True</managerial>
				</properties>
				<pay value="4.50"></pay>
				<pay value="4.30"></pay>
				<pay value="6.50"></pay>
			</name>
		'''))
	
	Args:
		name : str -- Name of argument to pass the value into the function with
		path : str -- XPath location to find value of variable in XML Element
		
		required : bool -- Whether the given value must be present in the XML Element
			NOTE: If True and no value is found a ValueError will be raised
		multiple : bool -- Whether multiple instances of the value should be expected
			NOTE: If False and multiple values are encountered the last will be provided
		parser : str -> Any -- Function used to convert the value from the element into the desired value
	
	Returns:
		(... -> T) -> (xml.etree.ElementTree.Element -> T) -- A decorator which converts allows a function to take an XML Element
	"""
	
	def decorator(func):
		# Only wrap `func` if it hasn't already been wrapped by fromXML
		if hasattr(func, '__fromXML'):
			func.__fromXML[name] = (path, required, multiple, parser, default)
			return func
		
		# Wrapped function takes an XML element
		argparsers = {name: (path, required, multiple, parser, default)}
		@wraps(func)
		def wrapped(*args, **kwargs):
			if 'xml' in kwargs:
				# Get the xml element
				elem = kwargs['xml']
				del kwargs['xml']
			else:
				# Otherwise nothing to process
				return func(*args, **kwargs)
			
			new_kwargs = {}
			for name, (path, required, multiple, parser, default) in argparsers.items():
				contents = xpath(elem, path)
				
				# If the value is required but not present error
				if required and len(contents) == 0:
					raise ValueError("Required argument %s was not found at path %s in Element %s" % (name, path, str(elem)))
				
				# If only one value is desired get the last
				if multiple:
					# Try parsing the value with `parser`
					if parser is not None:
						contents = list(map(parser, contents))
				elif len(contents) > 0 :
					contents = contents[-1]
					# Try parsing the value with `parser`
					if parser is not None:
						contents = parser(contents)
				else:
					contents = default  # Set new_kwargs[name] with default since value is missing
				
				new_kwargs[name] = contents
			
			# Update the new_kwargs with the old kwargs
			# This ensures that any keyword arguments passed to the wrapped
			#    function will overwrite those extracted from the XML
			new_kwargs.update(kwargs)
			
			return func(*args, **new_kwargs)
		
		# Add parsers to function
		wrapped.__fromXML = argparsers
		return wrapped
	
	return decorator




class NamedMixin:
	"""
	An object which is can be identified by multiple different aliases
	One of which is the primary (i.e. self.name)
	"""
	
	def initNames(self, name, aliases):
		"""
		Set the name and aliases of a NamedMixin
		Checking the values for validity
		"""
		
		if type(name) != str:
			raise TypeError("Name of NamedMixin must be a string")
		elif any(type(al) != str for al in aliases):
			raise TypeError("Aliases of NamedMixin must be a string")
		
		self.name = name
		self.aliases = set(aliases)
	
	@property
	def __lowered(self):
		""" Get the set of names and aliases in lowercase """
		return {al.lower() for al in self.aliases} | {self.name.lower()}
	
	def __eq__(self, other):
		""" NamedMixins are considered equal if they have any overlapping names """
		
		return isinstance(other, NamedMixin) and len(self.__lowered & other.__lowered) > 0
	
	def __neq__(self, other):
		return not self.__eq__(other)
	
	def __contains__(self, name):
		""" Check if this NamedMixin has this name as its name or alias ignoring case """
		
		if type(name) == str:
			return name.lower() in self.__lowered
		else:
			# This behavior can be avoided in subclasses by
			# Overriding this method and wrapping it in a try-except
			raise TypeError("NamedMixin can only contain strings")
	
	def __str__(self):
		return self.name
	
	def merge(self, other):
		"""
		Merge a single alias, list of aliases, or the name
		and aliases of a NamedMixin into this NamedMixin
		
		Signature:
			merge(alias: str) -- Add a single name to the set of aliases
			merge(aliases: [str]) -- Add all of the names from an iterable
			merge(named: NamedMixin) -- Add the name and aliases of another NamedMixin
		"""
		
		if type(other) == str:
			self.aliases.add(other)
		elif isinstance(other, NamedMixin):
			self.aliases.add(other.name)
			self.aliases |= other.aliases
		elif hasattr(other, '__iter__'):
			other = set(other)
			
			# Make sure they are all strings
			if any(type(al) != str for al in other):
				raise TypeError('Only string elements can be merged into a NamedMixin')
			
			self.aliases |= other
		else:
			raise TypeError('')


