# -*- coding: utf-8 -*-
"""
	openweathermapy.core
	~~~~~~~~~~~~~~~~~~~~
	Core module containing functions and classes to fetch and handle data from
	*OpenWeatherMap.org*. It wraps API 2.5. Items of returned data (mostly nested
	dictionaries) can be accessed in a simplified and flexible way:

	   # openweathermapy access
	   >>> item = data("main.temp")
	   
	   # equals
	   >>> item = data["main"]["temp"]

	   # multiple items can be fetched at once by passing a list of keys
	   >>> items = data(["main.temp", "wind.speed"])

	Base functions and classes to handle nested dictionaries are located
	in `openweathermapy.utils`.

	For a complete list of `**params`, which can be passed to the functions
	in this module, refer to API documentation on http://openweathermap.org.
	They always depend on the request, but unsupported parameters
	will (normally) not raise an error. Most common ones to be used are "units",
	"lang" and (if needed) "APIKEY". So, it may be a good idea to pass them in
	form of a settings dictionary:

	   >>> settings = {"units": "metric", "lang": "de"}
	   >>> data = get_current("Kassel,de", **settings)

	:copyright: (c) 2015 by Stefan Kuethe.
	:license: GPLv3, see <http://www.gnu.org/licenses/gpl.txt> for more details.
"""
import functools
import json
from . import utils

__author__ = "Stefan Kuethe"
__license__ = "GPLv3"

# ("Kassel,DE", "Malaga,ES", "New York,US")
CITIES = (2892518, 2514256, 5128581)

# Geographic coordinates for "Kassel,DE"
KASSEL_LATITUDE = 51.32
KASSEL_LONGITUDE = 9.5
KASSEL_LOC = (KASSEL_LATITUDE, KASSEL_LONGITUDE)

BASE_URL="http://api.openweathermap.org/data/2.5/"
URL_ICON = "http://openweathermap.org/img/w/%s.png" 

def get(url, **params):
	"""Return data as (nested) dictionary for `url` request."""
	data = utils.get_url_response(url, **params)
	# Decoding: Python3 compatibility
	return json.loads(data.decode("utf-8"))

def wrap_get(appendix, settings=None):
	"""Wrap `get` function by setting url to `BASE_URL+appendix`.

	Moreover, as optinal argument `loc` can be passed to
	wrapped function, where loc can either be a (city) name, a (city) id
	or geographic coordinates.
	"""
	url = BASE_URL+appendix
	def call(loc=None, **params):
		if loc:
			params["loc"] = loc
			if type(loc) == int:
				params["id"] = loc
			elif type(loc) == tuple:
				params.update({"lat": loc[0], "lon": loc[1]})
			else:
				params["q"] = loc
		if settings:
			params.update(settings)
		data = get(url, **params)
		return data
	return call


class Decorator(object):
	"""Decorator for `get`.

	Gives more or less same functionality as `get_wrap`,
	except that `data_type` can be passed and furthermore,
	it is *real* decorator! 
	"""
	def __init__(self, appendix, settings=None, data_type=None):
		self.get = wrap_get(appendix, settings)

	def __call__(self, f):
		@functools.wraps(f)
		def call(*args, **kwargs):
			params = f(*args, **kwargs)
			data = self.get(**params)
			if data_type:
				data = data_type(data)
			return data
		return call

def get_icon_url(weather_data):
	"""Get icon url from `weather_data`."""
	icon = weather_data["weather"][0]["icon"]
	return URL_ICON %icon

class DataBlock(utils.NestedDictList):
	"""Class for all OWM responses containing list with weather data."""
	def __init__(self, data):
		utils.NestedDictList.__init__(self, data.pop("list"))
		self.info = utils.NestedDict(data)

class WeatherData(utils.NestedDict):
	def get_icon_url(self):
		#return self["weather"][0]["icon"]
		return get_icon_url(self)

def get_current(city=None, **params):
	"""Get current weather data for `city`.
	
	Args:
	   city (str, int or tuple): either city name, city id
	      or geographic coordinates (latidude, longitude)
	   **params: units, lang[, zip]

	Examples:
	   # get data by city name and country code
	   >>> data = get_current("Kassel,de")

	   # get data by city id and set language to german (de)
	   >>> data = get_current(2892518, lang="de")

	   # get data by latitude and longitude and return temperatures in Celcius
	   >>> location = (51.32, 9.5)
	   >>> data = get_current(location, units="metric")

	   # optinal: skip city argument and get data by zip code
	   >>> data = get_current(zip="34128,de") 
	"""
	data = wrap_get("weather")(city, **params)
	return WeatherData(data)

def get_current_for_group(city_ids, **params):
	"""Get current weather data for multiple cities.

	Args:
	   city_ids (tuple): list of city ids,
	   **params: units, lang

	Example:
	   # get data for 'Malaga,ES', 'Kassel,DE', 'New York,US'
	   >>> data = get_current_group((2892518, 2514256, 5128581), units="metric")
	"""
	id_str = ",".join([str(id_) for id_ in city_ids])
	params["id"] = id_str 
	data = wrap_get("group")(**params)
	return DataBlock(data)

def find_city(city, **params):
	"""Search for `city` and return current weather data for match(es).

	Examples:
	   >>> data = find_city("New York")
	   >>> data = find_city("Malaga,ES")
	"""
	data = wrap_get("find")(city, **params)
	return data

def find_cities_by_geo_coord(geo_coord=None, count=10, **params):
	"""Get current weather data for cities around `geo_coord`.

	Note: Country code is not submitted in response!
	
	Args:
	   geo_coord (tuple): geographic coordinates (latidude, longitude)
	   count (int): number of cities to be returned,
	      defaults to 10
	   **params: units, lang
	"""
	params["cnt"] = count
	data = wrap_get("find")(geo_coord, **params)
	return DataBlock(data)

def get_current_from_station(station_id=None, **params):
	"""Get current weather data from station."""
	data = wrap_get("station")(station_id, **params)
	return data

def find_stations_by_geo_coord(geo_coord=None, **params):
	"""Same as `find cities_by_geo_coord` but for stations instead of cities."""
	data = wrap_get("station/find")(geo_coord, **params)
	return DataBlock(data)

def get_forecast_hourly(city=None, **params):
	"""Get 3h forecast data for `city`.

	Args: same as for `get_current` 
	"""
	data = wrap_get("forecast")(city, **params)
	return DataBlock(data)

def get_forecast_daily(city=None, **params):
	"""Get daily forcast data for `city`.

	Args: same as for `get_current`
	"""
	data = wrap_get("forecast/daily")(city, **params)
	return DataBlock(data)

def get_history(city=None, **params):
	"""Get historical data for `city`.

	Note: Tests (without API-KEY) did not work very well until now!

	Args:
	   **parmas: see OpenWeatherMap.org's API 2.5 for details,
	      everything can be passed!
	"""
	data = wrap_get("history/city")(city, **params)
	return data

