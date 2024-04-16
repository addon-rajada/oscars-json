# -*- coding: utf-8 -*-
# Copyright (C) 2024 gbchr

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from pprint import pprint
from threadpool import indexed_threadpool
from tmdb import QuerySearch

cached_titles = {}
cached_hits = 0
total_searches = 0
total_movies_found = 0
total_movies_not_found = 0
total_persons_found = 0
total_persons_not_found = 0
invalid_year_results = []

def get_soup(year):
	headers = {
		'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36',
	}
	year_url = 'https://www.oscars.org/oscars/ceremonies/%s?qt-honorees=0#qt-honorees'
	response = requests.get(year_url % year, headers=headers)
	soup = BeautifulSoup(response.text, "html.parser")
	decoded = soup.encode('latin-1').decode('utf-8', errors='ignore')
	return BeautifulSoup(decoded, "html.parser")

def get_dict_from_movie(response):
	return {
		'id': response['results'][0]['id'],
		'original_title': response['results'][0]['original_title'],
		'title': response['results'][0]['title'],
		'release_date': response['results'][0]['release_date'],
		'backdrop_path': response['results'][0]['backdrop_path'],
		'poster_path': response['results'][0]['poster_path'],
		'overview': response['results'][0]['overview'],
		'vote_average': response['results'][0]['vote_average'],
		'vote_count': response['results'][0]['vote_count'],
		'result_type': 'movie',
	}

def get_dict_from_person(response):
	return {
		'id': response['results'][0]['id'],
		'gender': response['results'][0]['gender'],
		'known_for_department': response['results'][0]['known_for_department'],
		'name': response['results'][0]['name'],
		'original_name': response['results'][0]['original_name'],
		'popularity': response['results'][0]['popularity'],
		'profile_path': response['results'][0]['profile_path'],
		#'known_for': response['results'][0]['known_for'][:2],
		'result_type': 'person',
	}

def get_ids(title, second_label, year):

	global cached_titles, cached_hits, total_searches, invalid_year_results
	global total_movies_found, total_movies_not_found, total_persons_found, total_persons_not_found
	if title in cached_titles.keys():
		cached_hits += 1
		return cached_titles[title]

	query = '%s' % (title)
	response = QuerySearch('movie', query, int(year) - 1)
	total_searches += 1
	try:
		release = response['results'][0]['release_date']
		release_year = int(release[:4])
		result = get_dict_from_movie(response)
		total_movies_found += 1

		if release_year not in [int(year) + 1, int(year), int(year) - 1, int(year) - 2, int(year) - 3]: # check if is a valid movie result for given year. may occur outliers
			invalid_year_results.append({
				'title': title,
				'year': year,
				'result': result,
			})
			result = {'error': 'no ID found'}
			total_movies_found -= 1
			total_movies_not_found += 1
			
		#cached_titles[title] = result
		#print(f"found {response['results'][0]['original_title']} for {title}")
	except:

		response_person = QuerySearch('person', title, int(year) - 1)
		total_searches += 1

		response_movie = None
		searched_movie = False
		if second_label in cached_titles.keys():
			cached_hits += 1
			response_movie = cached_titles[second_label]
		else:
			response_movie = QuerySearch('movie', second_label, int(year) - 1)
			searched_movie = True
			total_searches += 1

		try:
			result = get_dict_from_person(response_person)
			total_persons_found += 1
			try:
				result['award_movie'] = get_dict_from_movie(response_movie)
				#cached_titles[second_label] = get_dict_from_movie(response_movie)
				if searched_movie: total_movies_found += 1
			except:
				result['award_movie'] = {'error': 'no ID found'}
				#cached_titles[second_label] = {'error': 'no ID found'}
				if searched_movie: total_movies_not_found += 1

			cached_titles[title] = result
		except:
			result = {'error': 'no ID found'}
			total_persons_not_found += 1

			try:
				result['award_movie'] = get_dict_from_movie(response_movie)
				#cached_titles[second_label] = get_dict_from_movie(response_movie)
				if searched_movie: total_movies_found += 1
			except:
				result['award_movie'] = {'error': 'no ID found'}
				#cached_titles[second_label] = {'error': 'no ID found'}
				if searched_movie: total_movies_not_found += 1

			cached_titles[title] = result
		
	return result

def process_noms(id, nom, cat, year):
	l1 = nom.find('div', {'class': 'field--name-field-award-entities'}).getText().strip() # first label
	l2 = nom.find('div', {'class': 'field--name-field-award-film'}).getText().strip() # second label
	#print(f'nominees for {cat} {year}: {l1} / {l2}')
	r = {
		'first_label': l1,
		'second_label': l2,
		'category': cat,
		'year': year,
		'tmdb': get_ids(l1, l2, year) # l1/l2 can be movie or person
	}
	return (id, r)

def process_group(id, g, year):
	results_array = []
	cat = g.find('div', {'class':'field--name-field-award-category-oscars'}, recursive=True).getText().strip() # category name
	print(f'category name: {cat} {year}')
	noms = g.find_all('div', {'class': 'paragraph--type--award-honoree'}, recursive=True) # nominees container
	counter = 0
	result = indexed_threadpool(process_noms, [(nom,cat,year) for nom in noms], {'nom':0, 'cat':1, 'year':2}, max_threads=2)
	for r in result:
		r['winner'] = True if counter < 1 else False # first result is winner
		results_array.append(r)
		counter += 1
	return (id, (cat, results_array))

def year_data_by_film(year): # recent ceremonies doesn't have this tab, not using it
	soup = get_soup(year)
	by_film = soup.select('div.view-display-id-osc_honoree_by_film')[0]
	groups = by_film.find('div', {'class': 'view-content'}).find_all('div', {'class': 'view-grouping'}, recursive=False)
	for g in groups:
		films = g.find_all('div', {'class': 'view-grouping'}, recursive=True)
		for f in films:
			name = f.find('div', {'class': 'view-grouping-header'}).getText().strip()
			print(name)
			break
		break

def year_data_by_cat(id, year):
	soup = get_soup(year)
	by_cat = soup.select('div#view-by-category-pane')[0] # view by category

	groups = by_cat.find('div', {'class': 'field--name-field-award-categories'}) # second div
	groups = groups.find_all('div', {'class': 'field__item'}, recursive=False) # entries
	#print(f'found {len(groups)} groups')

	processed_groups = indexed_threadpool(process_group, [(g, year) for g in groups], {'g':0,'year':1}, max_threads=3)
	data_dict = {}
	for g in processed_groups:
		data_dict[g[0]] = g[1]
		
	return (id, (year, data_dict))

def main():

	global cached_hits, total_searches, invalid_year_results
	global total_movies_found, total_movies_not_found, total_persons_found, total_persons_not_found

	start_year = 2022
	end_year = 2025 #datetime.now().year + 1
	years = [[y] for y in range(start_year, end_year)]

	#final_result = {}
	result = indexed_threadpool(year_data_by_cat, years, {'year': 0}, show_progress=True, max_threads=3)
	for r in result:
		#final_result[r[0]] = r[1]
		with open('year/%s.json' % r[0], 'w') as f:
			j = json.dumps(r[1], indent=4)
			print(j, file = f)

		invalid_tmdb = [x for x in invalid_year_results if x['year'] == r[0]]
		if len(invalid_tmdb) > 0:
			with open('invalid_tmdb_results/%s.json' % r[0], 'w') as f:
				j = json.dumps(invalid_tmdb, indent=4)
				print(j, file = f)
	
	
	print(f'cached hits: {cached_hits}')
	print(f'total searches: {total_searches}')
	print(f'invalid year results: {len(invalid_year_results)}')
	print(f'total movies found: {total_movies_found}')
	print(f'total movies not found: {total_movies_not_found}')
	print(f'total persons found: {total_persons_found}')
	print(f'total persons not found: {total_persons_not_found}')

	#with open('invalid_year_results.json', 'w') as fy:
	#	j = json.dumps(invalid_year_results, indent=4)
	#	print(j, file = fy)

	#with open('oscars.json', 'w') as fj:
	#	j = json.dumps(final_result, indent=4)
	#	print(j, file = fj)

main()
