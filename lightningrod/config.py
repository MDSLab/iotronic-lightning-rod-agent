import os, pkg_resources
dist = pkg_resources.get_distribution("iotronic-lightning-rod-agent")
entry_points_name = os.path.join(dist.location, dist.egg_name()) + ".egg-info/entry_points.txt"
#print entry_points_name