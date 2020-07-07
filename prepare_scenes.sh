find . -name '*.py' | xargs grep -r "(Scene)*" | awk '/class/{gsub(".*class",""); print $0}'| awk '/Scene/{gsub("\\(Scene\\):",""); print $0}'| awk '//{gsub(" ",""); print $0}'  > raw_scene_list.txt

# Dedup raw_scene_list
cp raw_scene_list.txt raw_scene_list.txt.bak
sort -u raw_scene_list.txt > sorted_raw_scene_list.txt
mv sorted_raw_scene_list.txt raw_scene_list.txt

find MEDIA_DIR -name '*.mp4' | awk '/mp4/{gsub(".*/",""); print $0}' | awk '/mp4/{gsub("Temp.mp4",""); print $0}' | awk '/mp4/{gsub(".mp4",""); print $0}' > done_list.txt
# Dedup done_list
cp done_list.txt done_list.txt.bak
sort -u done_list.txt > sorted_done_list.txt
mv sorted_done_list.txt done_list.txt

comm -23 raw_scene_list.txt done_list.txt > pending.txt

find . -name '*.py' | xargs grep -r "(Scene)*"| awk '/class/{gsub(":class",""); print $0}' |  awk '/py/{gsub("\\(Scene\\):"," -pl"); print $0}' | awk '/py/{gsub("\\(SceneFromVideo\\):"," -pl"); print $0}' | awk '/.py/{gsub("\\./","python extract_scene.py "); print $0}'> extract_scene_cmd.sh

#awk '/class/{gsub("./","python extract_scene.py "); print $0}' 

python update_extract_scene_cmd.py
cp extract_scene_cmd.sh extract_scene_cmd.sh.bak
mv extract_scene_cmd_modified.sh extract_scene_cmd.sh

