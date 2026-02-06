import os
import sys
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError

def print_mp3_tags(filepath):
    """
    Prints the ID3 tags of an MP3 file.

    Args:
        filepath (str): The path to the MP3 file.
    """
    # Check if the file exists
    if not os.path.exists(filepath):
        print(f"Error: The file '{filepath}' was not found.")
        return

    try:
        # Load the MP3 file with EasyID3, which makes common tags easier to access
        audio = EasyID3(filepath)
        
        print(f"--- Tags for '{os.path.basename(filepath)}' ---")
        
        # Check if any tags were found
        if not audio:
            print("No tags found.")
            return

        # Iterate over the tags and print them
        for key, value in audio.items():
            # Join list values into a single string for cleaner output
            formatted_value = value
            print(f"{key.replace('_', ' ').title()}: {formatted_value}")
            
    except ID3NoHeaderError:
        print("Error: No ID3 tags found in the file.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # Check for a command-line argument
    if len(sys.argv) < 2:
        print("Usage: python mp3_reader.py <path_to_mp3_file>")
    else:
        # Get the file path from the command-line arguments
        file_path = sys.argv[1]
        print_mp3_tags(file_path)
