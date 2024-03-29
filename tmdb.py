# -*- coding: utf-8 -*-
# Copyright (C) 2024 gbchr

import requests

API_key = 'bc96b19479c7db6c8ae805744d0bdfe2'
lang = 'pt-BR'

search_url = 'https://api.themoviedb.org/3/search/%s?query=%s&api_key=%s&page=%s&language=%s&year=%s&sort_by=%s' % ('%s', '%s', API_key, '%s', lang, '%s', '%s')

def get_request(url, timeout = 15):
	try:
		try: response = requests.get(url, timeout=timeout)
		except requests.exceptions.SSLError:
			response = requests.get(url, verify=False, timeout=timeout)
	except requests.exceptions.ConnectionError:
		pass
	if '200' in str(response):
		return response.json()
	elif 'Retry-After' in response.headers: # API REQUESTS ARE BEING THROTTLED, INTRODUCE WAIT TIME (TMDb removed rate-limit on 12-6-20)
		throttleTime = response.headers['Retry-After']
		return get_request(url, timeout=timeout)
	else:
		return None

def QuerySearch(type, query, year, page = 1):
	result = None
	try:
		sortBy = 'popularity.desc' # 'vote_count'
		if type == 'tvshow': type = 'tv'
		url = search_url % (type, query, page, year, sortBy)
		result = get_request(url)
		if not result: raise Exception()
	except:
		pass
	return result
