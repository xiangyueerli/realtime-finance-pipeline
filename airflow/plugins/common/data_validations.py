import os
import json

def validate_transcript_file(file_path, min_transcript_length=100):
    """
    Validate the transcript file for errors such as empty, corrupted, or short content.
    
    Args:
        file_path (str): Path to the JSON file.
        min_transcript_length (int): Minimum length of the transcript to be considered valid.
    
    Returns:
        dict: Parsed JSON data if valid.
        None: If the file is invalid.
    """
    try:
        # Check if the file exists and is not empty
        if not os.path.exists(file_path):
            print(f"Error: File does not exist - {file_path}")
            return None
        
        if os.path.getsize(file_path) == 0:
            print(f"Error: File is empty - {file_path}")
            return None

        # Load the JSON file
        with open(file_path, 'r') as file:
            data = json.load(file)

        # Check if required keys are present
        if "date" not in data or "transcript" not in data:
            print(f"Error: Missing required keys in file - {file_path}")
            return None

        # Check if the transcript is too short
        transcript = data["transcript"]
        if len(transcript) < min_transcript_length:
            print(f"Error: Transcript is too short ({len(transcript)} characters) - {file_path}")
            return None

        # File is valid
        return data

    except json.JSONDecodeError:
        print(f"Error: Corrupted JSON file - {file_path}")
        return None
    except Exception as e:
        print(f"Error: Unexpected error while validating file - {file_path}. Error: {e}")
        return None