# -*- coding: utf-8 -*-
# Copyright (C) 2024 gbchr

from concurrent.futures import ThreadPoolExecutor, as_completed

def indexed_threadpool(function, data, func_args, max_threads = 16, show_progress = False):
	"""
		function MUST have following signature -> (id, arg1, arg2, ...) and return -> (id, ...)
		data MUST be an array of List, Tuple or Object
		func_args MUST be an object:
			{
				'arg1': index/key for each item at data array,
				...
			}
		example:
			def myfunc(id, value1, value2): return (id, value1*value2)
			values = [[1,2],[2,3],[3,4],[4,5],[5,6]]
			result = indexed_threadpool(myfunc, values, {'value1':0, 'value2':1})
	"""
	size = len(data)
	workers = size if (size > 0 and size <= max_threads) else max_threads
	counter = 0
	done = 0
	final_result = []
	with ThreadPoolExecutor(max_workers = workers) as executor:
		futures = []
		for item in data:
			args_dict = {'id': counter}
			for argument, index in func_args.items(): args_dict[argument] = item[index]
			futures.append(executor.submit(function, **args_dict))
			args_dict = {}
			counter += 1
		for f in as_completed(futures):
			result = f.result()
			final_result.append(result)
			done += 1
			if show_progress: print(f"done {done}/{size} for {str(function)}")
	return [value[1] for value in sorted(final_result, key = lambda x: x[0])] # sort by id then remove it
