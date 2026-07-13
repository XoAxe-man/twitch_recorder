#!/bin/bash
# /opt/scripts/transcode_vod.sh
# Remote transcoding helper executed over SSH from the recorder host.
# It remuxes the raw Twitch .ts file, encodes video with NVIDIA hardware,
# extracts the audio track, and writes the final files back to the shared
# destination path.

RAW_INPUT="$1"

# Translate the recorder container path into the local mount path used by
# the transcoding machine.
INPUT_FILE="${RAW_INPUT/\/VOD\//\/mnt\/vod\/}"
BASENAME=$(basename "$INPUT_FILE")
FILENAME="${BASENAME%.ts}"
DIRNAME=$(dirname "$INPUT_FILE")

# Local temporary workspace for intermediate outputs.
LOCAL_REMUX="/home/axe-man/tmp/${FILENAME}_remux.mkv"
LOCAL_FINAL_VID="/home/axe-man/tmp/${FILENAME}.mkv"
FINAL_DEST_VID="$DIRNAME/$FILENAME/$FILENAME.mkv"

LOCAL_FINAL_AUD="/home/axe-man/tmp/${FILENAME}.wav"
FINAL_DEST_AUD="$DIRNAME/$FILENAME/$FILENAME.wav"

# Remux the incoming TS file into a stable MKV container for encoding.
/usr/bin/ffmpeg -y -i "$INPUT_FILE" -c copy "$LOCAL_REMUX"

if [ $? -eq 0 ]; then
   # Encode video using CUDA hardware acceleration.
   /usr/bin/ffmpeg -y -hwaccel cuda -hwaccel_output_format cuda -i "$LOCAL_REMUX" \
      -c:v h264_nvenc -preset p4 -profile:v high -b:v 8000k -an \
      -avoid_negative_ts make_zero -write_tmcd 0 -loglevel error "$LOCAL_FINAL_VID" 2> ~/"Logs/${FILENAME}_VID.log"

   VID_STATUS=$?

   # Extract the audio track as a WAV file.
   /usr/bin/ffmpeg -y -i "$LOCAL_REMUX" -vn -c:a pcm_s16le -rf64 auto -loglevel error "$LOCAL_FINAL_AUD" 2> ~/"Logs/${FILENAME}_AUD.log"

   AUD_STATUS=$?

   if [ $VID_STATUS -eq 0 ] && [ $AUD_STATUS -eq 0 ]; then
       mkdir -p "$DIRNAME/$FILENAME"
       cat "$LOCAL_FINAL_VID" > "$FINAL_DEST_VID"
       CAT_VID_STS=$?
       cat "$LOCAL_FINAL_AUD" > "$FINAL_DEST_AUD"
       CAT_AUD_STS=$?
      if [ $CAT_VID_STS -eq 0 ] && [ $CAT_AUD_STS -eq 0 ]; then
         rm "$LOCAL_FINAL_VID" "$LOCAL_FINAL_AUD"
         rm "$INPUT_FILE"
         rm "$LOCAL_REMUX"
      else
         echo "Error: Final file copy failed"
         exit 1
fi
