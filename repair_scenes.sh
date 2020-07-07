find MEDIA_DIR -name '*.mp4' | awk '/mp4/{gsub(".*/",""); print $0}' | awk '/mp4/{gsub("Temp.mp4",""); print $0}' | awk '/mp4/{gsub(".mp4",""); print $0}' > done_list.txt
# Dedup done_list
cp done_list.txt done_list.txt.bak
sort -u done_list.txt > sorted_done_list.txt
mv sorted_done_list.txt done_list.txt

comm -23 raw_scene_list.txt done_list.txt > pending.txt

python update_extract_scene_cmd.py
cp extract_scene_cmd.sh extract_scene_cmd.sh.bak
mv extract_scene_cmd_modified.sh extract_scene_cmd.sh

