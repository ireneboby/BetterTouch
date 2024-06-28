import cProfile, pstats, io

with open('bettertouch.txt', 'w') as stream:
    stats = pstats.Stats('bettertouch.prof', stream=stream)
    stats.sort_stats(2).print_stats()