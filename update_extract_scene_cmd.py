import os, datetime, time, sys, pickle

done_arr = []
with open("done_list.txt", "r") as infile:
    Vs = infile.readlines()
    for v in Vs:
        v =v[:-1]
        done_arr.append(v)
# print(done_arr)

with open("extract_scene_cmd_modified.sh", "w") as outfile:
    with open("extract_scene_cmd.sh", "r") as infile:
        Vs = infile.readlines()
        for v in Vs:
            c = v[:-1].split(' ')[-2]
            if c not in done_arr:
                outfile.write(v)
