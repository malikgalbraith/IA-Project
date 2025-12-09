import html
"""
Module for generating output files from transcription and analysis results.

Handles:
- Text file saving (transcripts, analysis)
- HTML report generation with formatted bullet points
- Title case formatting for report headlines
- File system operations for output

Outputs:
- .txt files for raw transcripts and analysis
- .html files for formatted research reports
"""
import logging
from pathlib import Path
from datetime import datetime
import textwrap
import re
from typing import List, Dict, Any, Optional

def format_display_date(raw_upload_date: Any, short: bool = False) -> str:
    """
    Formats upload date strings with an option for a short MM/DD/YY variant.
    Falls back to the raw string when parsing fails.
    """
    display_date = "Date Unknown"
    if not raw_upload_date:
        return display_date

    raw_str = str(raw_upload_date).strip()

    # Allow already formatted dates to pass through unchanged
    if "/" in raw_str and short:
        return raw_str

    try:
        dt_obj = datetime.strptime(raw_str, "%Y%m%d")
        return dt_obj.strftime("%m/%d/%y" if short else "%B %d, %Y")
    except (ValueError, TypeError):
        # If parsing fails, return the raw string
        return raw_str or display_date


def format_duration_value(duration_value: Any) -> Optional[str]:
    """
    Formats a duration value in seconds into a friendly string.
    Examples: 5700 -> '1h 35m', 185 -> '3m 5s'
    """
    if duration_value is None:
        return None
    try:
        total_seconds = float(duration_value)
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)

        if hours > 0:
            if seconds:
                return f"{hours}h {minutes}m {seconds}s"
            return f"{hours}h {minutes}m"
        return f"{minutes}m {seconds}s"
    except Exception:
        return str(duration_value)

def _title_case_word(word: str) -> str:
    """
    Helper function to apply specific title casing rules to a single word.

    This function handles special cases like acronyms, hyphenated words,
    and preserves leading/trailing punctuation. It also keeps a list of
    common words that should remain lowercase in a title.

    Args:
        word: The single word string to title case.

    Returns:
        The title-cased word according to the defined rules.
    """
    if not word:
        return ""

    # Preserve case for acronyms (e.g., U.S.A.)
    if re.match(r'^([A-Z]\.)+$', word):
        return word
    # Preserve case for all-uppercase words longer than one character (e.g., NASA)
    if word.isupper() and len(word) > 1:
        return word
    # Recursively process hyphenated words
    if '-' in word and len(word) > 1:
        return '-'.join(_title_case_word(part) for part in word.split('-'))

    # Find the first and last alphabetic characters to isolate the core word
    first_alpha_index = -1
    last_alpha_index = -1
    for i, char in enumerate(word):
        if char.isalpha():
            if first_alpha_index == -1:
                first_alpha_index = i
            last_alpha_index = i

    # If no alphabetic characters are found, return the original word
    if first_alpha_index == -1:
        return word

    # Split the word into leading punctuation, the core word, and trailing punctuation
    leading_punct = word[:first_alpha_index]
    core_word = word[first_alpha_index : last_alpha_index + 1]
    trailing_punct = word[last_alpha_index + 1 :]

    # Define a set of common words that should remain lowercase in titles
    # Apply capitalization rules to the core word
    capitalized_core = core_word.capitalize()  # Capitalize the first letter

    # Reassemble the word with original punctuation
    return leading_punct + capitalized_core + trailing_punct

def apply_strict_title_case_every_word(text: str) -> str:
    """
    Applies strict title case formatting to every word in a string.

    This function splits the input text into words, applies the `_title_case_word`
    helper function to each word, and then joins them back together. It also
    ensures that the very first alphabetic character of the resulting string
    is capitalized, regardless of whether it's a common lowercase word.

    Args:
        text: The input string to title case.

    Returns:
        The string with strict title case applied to each word.
    """
    if not text:
        return ""

    # Split the text into words and apply the helper function to each
    words = text.split(' ')
    title_cased_words = [_title_case_word(word) for word in words]
    result = ' '.join(title_cased_words)

    # Ensure the very first alphabetic character in the result is uppercase
    for i, char in enumerate(result):
        if char.isalpha():
            if not result[i].isupper():
                result = result[:i] + result[i].upper() + result[i+1:]
            break # Stop after capitalizing the first alphabetic character

    return result


def save_text_file(content: str, filepath: Path) -> bool:
    """
    Saves the given text content to a file at the specified path.

    This function ensures that the parent directories for the file exist,
    writes the content using UTF-8 encoding, and includes error handling
    for file system operations.

    Args:
        content: The string content to be written to the file.
        filepath: A `pathlib.Path` object representing the full path
                  to the output file.

    Returns:
        True if the file was saved successfully, False otherwise.
    """
    logging.info(f"Attempting to save text to: {filepath}")
    try:
        # Ensure the parent directory for the output file exists, creating it if necessary
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Open the file in write mode with UTF-8 encoding and write the content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        logging.info(f"Successfully saved text file: {filepath}")
        return True
    except IOError as e:
        # Handle specific IOError exceptions (e.g., permissions, disk space)
        logging.error(f"Failed to write text file {filepath}: {e}")
        return False
    except Exception as e:
        # Catch any other unexpected exceptions during the file saving process
        logging.error(f"An unexpected error occurred saving text file {filepath}: {e}", exc_info=True)
        return False

# Provide aliases for the save_text_file function for semantic clarity
save_transcript = save_text_file
save_analysis = save_text_file


def generate_report_highlights(
    metadata: Dict[str, Any],
    extracted_bullets_raw: List[Dict[str, Optional[str]]],
    transcript_text: str,
    target_name: str,
    html_or_docx: str
) -> str:
    """
    Generates a research report focused on highlights.
    When the target is "Debate", the report is formatted around the debate title,
    uses a short date style, and omits platform clutter to mirror the provided example.
    """
    logging.info(f"Generating HTML report for {target_name}...")
    print("extracted_bullets_raw", extracted_bullets_raw)

    is_debate = str(target_name).strip().lower() == "debate"
    report_prefix = "Tracking Report"

    title_value = metadata.get('title', '').strip()
    uploader = metadata.get('uploader', '').strip()
    extractor = metadata.get('extractor', '').strip()
    source_context = "Unknown Source"

    if uploader and uploader.lower() not in ['unknown uploader', 'n/a', '']:
        source_context = uploader
    elif extractor and extractor.lower() not in ['unknown', 'n/a', '']:
        source_context = extractor.replace('_', ' ').title()
        if source_context.lower() == 'youtube':
            source_context = 'YouTube'
        if source_context.lower() == 'vimeo':
            source_context = 'Vimeo'

    raw_upload_date = metadata.get('upload_date')
    display_date = format_display_date(raw_upload_date, short=is_debate)

    display_target = title_value if is_debate and title_value else target_name
    report_title = f"{report_prefix}: {display_target}" if is_debate else f"{report_prefix}: {target_name} via {source_context} ({display_date})"

    url = metadata.get('webpage_url', '#')
    duration_str = format_duration_value(metadata.get('duration'))

    html_parts = []
    if html_or_docx == "html":
        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"<title>Report: {display_target} - {source_context} ({display_date})</title>",
            "<meta charset=\"UTF-8\">",
            "<style>",
            """
            /* Base styles */
            body {
                font-family: Arial, sans-serif;
                font-size: 10pt;
                line-height: 1.15;
                margin: 0.5in;
            }
            
            .research-dossier {
                max-width: 7.5in;
                margin: 0 auto;
            }
            
            h1 {
                font-size: 18pt;
                font-weight: bold;
                text-align: center;
                border-bottom: 1px solid #000;
                padding-bottom: 6pt;
                margin-bottom: 18pt;
            }
            
            h2 {
                font-size: 12pt;
                font-weight: bold;
                color: white;
                background-color: black;
                padding: 4pt 6pt;
                margin: 24pt 0 12pt 0;
            }
            
            .meta {
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 24pt;
            }
            
            .meta p {
                margin: 4pt 0;
            }
            
            .bullets-list {
                list-style-type: disc;
                padding-left: 1.5em;
            }
            
            .bullets-list li {
                margin-bottom: 6pt;
                text-align: justify;
            }
            
            a {
                color: blue;
                text-decoration: underline;
            }
            
            a:visited {
                color: purple;
            }
            
            .transcript {
                white-space: pre-wrap;
                font-family: monospace;
                border: 1px solid #ddd;
                word-wrap: break-word;
                overflow-wrap: break-word;
            }
            """,
            "</style>",
            "</head>",
            "<body>",
            "<div class=\"research-dossier\">",
        ]

    html_parts.append(f"<h1>{html.escape(report_title)}</h1>")

    # --- Metadata Section ---
    html_parts.append("<div class=\"meta\">")
    html_parts.append(f"<p><strong>Title:</strong> {html.escape(title_value or display_target)}</p>")
    html_parts.append(f"<p><strong>Uploader/Channel:</strong> {html.escape(uploader or 'N/A')}</p>")
    html_parts.append(f"<p><strong>Upload Date:</strong> {display_date}</p>")
    if not is_debate:
        html_parts.append(f"<p><strong>Platform:</strong> {html.escape(extractor)}</p>")
    html_parts.append(f"<p><strong>URL:</strong> <a href=\"{html.escape(url)}\" target=\"_blank\">{html.escape(url)}</a></p>")
    if duration_str:
        html_parts.append(f"<p><strong>Duration:</strong> {duration_str}</p>")

    # --- Bullets Section ---
    html_parts.append("<h3>HIGHLIGHTS</h3>")
    html_parts.append("<ul class=\"bullets-list\">")
    if extracted_bullets_raw:
        for bullet_data in extracted_bullets_raw:
            logging.debug(f"Processing bullet_data: {bullet_data}")
            headline = bullet_data.get('headline_raw', 'N/A')
            source = bullet_data.get('source_raw', 'Unknown Source')
            raw_bullet_date = bullet_data.get('date_raw')
            formatted_date_mdy = 'Date Unknown'
            if raw_bullet_date:
                try:
                    dt_obj_bullet = datetime.strptime(str(raw_bullet_date), "%Y%m%d")
                    formatted_date_mdy = dt_obj_bullet.strftime("%#m/%#d/%y")
                except (ValueError, TypeError):
                    formatted_date_mdy = str(raw_bullet_date)

            safe_source = html.escape(source)
            safe_formatted_date_mdy = html.escape(formatted_date_mdy)

            if url and url != '#':
                safe_url = html.escape(url.replace('"', '"'))
                if not safe_url.startswith(('http://', 'https://')):
                    safe_url = 'http://' + safe_url
                safe_link_text = safe_formatted_date_mdy
                citation = f'[{safe_source}, <a href="{safe_url}" target="_blank" rel="noopener noreferrer"><em>{safe_link_text}</em></a>]'
            else:
                citation = f'[{safe_source}, {safe_formatted_date_mdy}]'

            safe_headline = html.escape(headline)
            html_parts.append(f"<li>{safe_headline}</li>")
    else:
        html_parts.append("<p>No relevant bullets were extracted. Using Highlights</p>")
    html_parts.append("</ul>")

    # --- Full Transcript Section ---
    html_parts.append("<h3>TRANSCRIPT</h3>")
    html_parts.append(transcript_text if transcript_text else "Transcript unavailable.")

    # --- Closing HTML ---
    html_parts.append("</div>")
    if html_or_docx == "html":
        html_parts.append("</body></html>")

    logging.info("HTML report string generated.")
    return "\n".join(html_parts)


def generate_report_bullets(
    metadata: Dict[str, Any],
    extracted_bullets_raw: List[Dict[str, Optional[str]]],
    transcript_text: str,
    target_name: str,
    html_or_docx: str
) -> str:
    """
    Generates a research report with detailed bullets.
    When the target is "Debate", the report leans on the debate title and uses a short date format.
    """
    logging.info(f"Generating HTML report for {target_name}...")

    is_debate = str(target_name).strip().lower() == "debate"
    report_prefix = "Tracking Report"

    title_value = metadata.get('title', '').strip()
    uploader = metadata.get('uploader', '').strip()
    extractor = metadata.get('extractor', '').strip()
    type_input = metadata.get('type_input', '').strip().upper()
    source_context = "Unknown Source"

    if uploader and uploader.lower() not in ['unknown uploader', 'n/a', '']:
        source_context = uploader
    elif extractor and extractor.lower() not in ['unknown', 'n/a', '']:
        source_context = extractor.replace('_', ' ').title()
        if source_context.lower() == 'youtube':
            source_context = 'YouTube'
        if source_context.lower() == 'vimeo':
            source_context = 'Vimeo'

    raw_upload_date = metadata.get('upload_date')
    display_date = format_display_date(raw_upload_date, short=is_debate)

    display_target = title_value if is_debate and title_value else target_name
    report_title = f"{report_prefix}: {display_target}" if is_debate else f"{report_prefix}: {target_name} via {source_context} ({display_date})"

    url = metadata.get('webpage_url', '#')
    duration_str = format_duration_value(metadata.get('duration'))

    html_parts = []
    if html_or_docx == "html":
        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"<title>Report: {display_target} - {source_context} ({display_date})</title>",
            "<meta charset=\"UTF-8\">",
            "<style>",
            """
            /* Base styles */
            body {
                font-family: Arial, sans-serif;
                font-size: 10pt;
                line-height: 1.15;
                margin: 0.5in;
            }
            
            .research-dossier {
                max-width: 7.5in;
                margin: 0 auto;
            }
            
            h1 {
                font-size: 18pt;
                font-weight: bold;
                text-align: center;
                border-bottom: 1px solid #000;
                padding-bottom: 6pt;
                margin-bottom: 18pt;
            }
            
            h2 {
                font-size: 12pt;
                font-weight: bold;
                color: white;
                background-color: black;
                padding: 4pt 6pt;
                margin: 24pt 0 12pt 0;
            }
            
            .meta {
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 24pt;
            }
            
            .meta p {
                margin: 4pt 0;
            }
            
            .bullets-list {
                list-style-type: disc;
                padding-left: 1.5em;
            }
            
            .bullets-list li {
                margin-bottom: 6pt;
                text-align: justify;
            }
            
            a {
                color: blue;
                text-decoration: underline;
            }
            
            a:visited {
                color: purple;
            }
            
            .transcript {
                white-space: pre-wrap;
                font-family: monospace;
                border: 1px solid #ddd;
                word-wrap: break-word;
                overflow-wrap: break-word;
            }
            """,
            "</style>",
            "</head>",
            "<body>",
            "<div class=\"research-dossier\">",
        ]

    html_parts.append(f"<h1>{html.escape(report_title)}</h1>")

    # --- Metadata Section ---
    html_parts.append("<div class=\"meta\">")
    html_parts.append(f"<p><strong>Title:</strong> {html.escape(title_value or display_target)}</p>")
    html_parts.append(f"<p><strong>Uploader/Channel:</strong> {html.escape(uploader or 'N/A')}</p>")
    html_parts.append(f"<p><strong>Upload Date:</strong> {display_date}</p>")
    if not is_debate:
        html_parts.append(f"<p><strong>Platform:</strong> {html.escape(extractor)}</p>")
        html_parts.append(f"<p><strong>File Type:</strong> {type_input}</p>")
    html_parts.append(f"<p><strong>URL:</strong> <a href=\"{html.escape(url)}\" target=\"_blank\">{html.escape(url)}</a></p>")
    if duration_str:
        html_parts.append(f"<p><strong>Duration:</strong> {duration_str}</p>")
    html_parts.append("</div>")

    # --- Bullets Section ---
    html_parts.append("<h3>BULLETS</h3>")
    html_parts.append("<div class=\"bullets-container\">")
    if extracted_bullets_raw:
        for bullet_data in extracted_bullets_raw:
            logging.debug(f"Processing bullet_data: {bullet_data}")
            headline = bullet_data.get('headline_raw', 'N/A')
            formatted_body = bullet_data.get('body_raw', 'N/A')
            source = bullet_data.get('source_raw', 'Unknown Source')
            raw_bullet_date = bullet_data.get('date_raw')
            formatted_date_mdy = 'Date Unknown'
            if raw_bullet_date:
                try:
                    dt_obj_bullet = datetime.strptime(str(raw_bullet_date), "%Y%m%d")
                    formatted_date_mdy = dt_obj_bullet.strftime("%#m/%#d/%y")
                except (ValueError, TypeError):
                    formatted_date_mdy = str(raw_bullet_date)

            safe_source = html.escape(source)
            safe_formatted_date_mdy = html.escape(formatted_date_mdy)

            if url and url != '#':
                safe_url = html.escape(url.replace('"', '"'))
                if not safe_url.startswith(('http://', 'https://')):
                    safe_url = 'http://' + safe_url
                safe_link_text = safe_formatted_date_mdy
                citation = f'[{safe_source}, <a href="{safe_url}" target="_blank" rel="noopener noreferrer"><em>{safe_link_text}</em></a>] ({type_input})'
            else:
                citation = f'[{safe_source}, {safe_formatted_date_mdy}] ({type_input})'

            title_cased_headline = apply_strict_title_case_every_word(headline)
            safe_headline = html.escape(title_cased_headline)
            safe_body = html.escape(formatted_body)

            html_parts.append("<div class=\"bullet\">")
            html_parts.append(f"<p><b>{safe_headline}</b> \"{safe_body}\" {citation}</p>")
            html_parts.append("</div>")
    else:
        html_parts.append("<p>No relevant bullets were extracted. Using Bullets</p>")
    html_parts.append("</div>")

    # --- Full Transcript Section ---
    html_parts.append("<h3>TRANSCRIPT</h3>")
    html_parts.append(transcript_text if transcript_text else "Transcript unavailable.")

    # --- Closing HTML ---
    html_parts.append("</div>")
    if html_or_docx == "html":
        html_parts.append("</body></html>")

    logging.info("HTML report string generated.")
    return "\n".join(html_parts)

#  REPORT FOR BOTH HIGHLIGHTS AND BULLETS
def generate_report_both(
    metadata: Dict[str, Any],
    extracted_bullets_raw: List[Dict[str, Optional[str]]],
    extracted_highlights_raw: List[Dict[str, Optional[str]]],
    transcript_text: str,
    target_name: str,
    html_or_docx: str
) -> str:
    """
    Generates a research report containing both highlights and bullets.
    When the target is "Debate", the report pivots to the debate title and short date format.
    """
    logging.info(f"Generating HTML report for {target_name}...")
    print("extracted_bullets_raw", extracted_bullets_raw)

    is_debate = str(target_name).strip().lower() == "debate"
    report_prefix = "Tracking Report"

    title_value = metadata.get('title', '').strip()
    uploader = metadata.get('uploader', '').strip()
    extractor = metadata.get('extractor', '').strip()
    type_input = metadata.get('type_input', '').strip().upper()
    source_context = "Unknown Source"

    if uploader and uploader.lower() not in ['unknown uploader', 'n/a', '']:
        source_context = uploader
    elif extractor and extractor.lower() not in ['unknown', 'n/a', '']:
        source_context = extractor.replace('_', ' ').title()
        if source_context.lower() == 'youtube':
            source_context = 'YouTube'
        if source_context.lower() == 'vimeo':
            source_context = 'Vimeo'

    raw_upload_date = metadata.get('upload_date')
    display_date = format_display_date(raw_upload_date, short=is_debate)

    display_target = title_value if is_debate and title_value else target_name
    report_title = f"{report_prefix}: {display_target}" if is_debate else f"{report_prefix}: {target_name} via {source_context} ({display_date})"

    url = metadata.get('webpage_url', '#')
    duration_str = format_duration_value(metadata.get('duration'))

    html_parts = []
    if html_or_docx == "html":
        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"<title>Report: {display_target} - {source_context} ({display_date})</title>",
            "<meta charset=\"UTF-8\">",
            "<style>",
            """
            /* Base styles */
            body {
                font-family: Arial, sans-serif;
                font-size: 10pt;
                line-height: 1.15;
                margin: 0.5in;
            }
            
            .research-dossier {
                max-width: 7.5in;
                margin: 0 auto;
            }
            
            h1 {
                font-size: 18pt;
                font-weight: bold;
                text-align: center;
                border-bottom: 1px solid #000;
                padding-bottom: 6pt;
                margin-bottom: 18pt;
            }
            
            h2 {
                font-size: 12pt;
                font-weight: bold;
                color: white;
                background-color: black;
                padding: 4pt 6pt;
                margin: 24pt 0 12pt 0;
            }
            
            .meta {
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 24pt;
            }
            
            .meta p {
                margin: 4pt 0;
            }
            
            .bullets-list {
                list-style-type: disc;
                padding-left: 1.5em;
            }
            
            .bullets-list li {
                margin-bottom: 6pt;
                text-align: justify;
            }
            
            a {
                color: blue;
                text-decoration: underline;
            }
            
            a:visited {
                color: purple;
            }
            
            .transcript {
                white-space: pre-wrap;
                font-family: monospace;
                border: 1px solid #ddd;
                word-wrap: break-word;
                overflow-wrap: break-word;
            }
            """,
            "</style>",
            "</head>",
            "<body>",
            "<div class=\"research-dossier\">",
        ]

    html_parts.append(f"<h1>{html.escape(report_title)}</h1>")

    # --- Metadata Section ---
    html_parts.append("<div class=\"meta\">")
    html_parts.append(f"<p><strong>Title:</strong> {html.escape(title_value or display_target)}</p>")
    html_parts.append(f"<p><strong>Uploader/Channel:</strong> {html.escape(uploader or 'N/A')}</p>")
    html_parts.append(f"<p><strong>Upload Date:</strong> {display_date}</p>")
    if not is_debate:
        html_parts.append(f"<p><strong>Platform:</strong> {html.escape(extractor)}</p>")
    html_parts.append(f"<p><strong>URL:</strong> <a href=\"{html.escape(url)}\" target=\"_blank\">{html.escape(url)}</a></p>")
    if duration_str:
        html_parts.append(f"<p><strong>Duration:</strong> {duration_str}</p>")

    # --- Highlights Section ---
    html_parts.append("<h3>HIGHLIGHTS</h3>")
    html_parts.append("<ul class=\"bullets-list\">")
    if extracted_highlights_raw:
        for bullet_data in extracted_highlights_raw:
            logging.debug(f"Processing bullet_data: {bullet_data}")
            headline = bullet_data.get('headline_raw', 'N/A')
            source = bullet_data.get('source_raw', 'Unknown Source')
            raw_bullet_date = bullet_data.get('date_raw')
            formatted_date_mdy = 'Date Unknown'
            if raw_bullet_date:
                try:
                    dt_obj_bullet = datetime.strptime(str(raw_bullet_date), "%Y%m%d")
                    formatted_date_mdy = dt_obj_bullet.strftime("%#m/%#d/%y")
                except (ValueError, TypeError):
                    formatted_date_mdy = str(raw_bullet_date)

            safe_source = html.escape(source)
            safe_formatted_date_mdy = html.escape(formatted_date_mdy)

            if url and url != '#':
                safe_url = html.escape(url.replace('"', '"'))
                if not safe_url.startswith(('http://', 'https://')):
                    safe_url = 'http://' + safe_url
                safe_link_text = safe_formatted_date_mdy
                citation = f'[{safe_source}, <a href="{safe_url}" target="_blank" rel="noopener noreferrer"><em>{safe_link_text}</em></a>]'
            else:
                citation = f'[{safe_source}, {safe_formatted_date_mdy}]'

            safe_headline = html.escape(headline)
            html_parts.append(f"<li>{safe_headline}</li>")
    else:
        html_parts.append("<p>No relevant bullets were extracted. Using Highlights</p>")
    html_parts.append("</ul>")
     
    # --- Bullets Section ---
    html_parts.append("<h3>BULLETS</h3>")
    html_parts.append("<div class=\"bullets-container\">")
    if extracted_bullets_raw:
        for bullet_data in extracted_bullets_raw:
            logging.debug(f"Processing bullet_data: {bullet_data}")
            headline = bullet_data.get('headline_raw', 'N/A')
            formatted_body = bullet_data.get('body_raw', 'N/A')
            source = bullet_data.get('source_raw', 'Unknown Source')
            raw_bullet_date = bullet_data.get('date_raw')
            formatted_date_mdy = 'Date Unknown'
            if raw_bullet_date:
                try:
                    dt_obj_bullet = datetime.strptime(str(raw_bullet_date), "%Y%m%d")
                    formatted_date_mdy = dt_obj_bullet.strftime("%#m/%#d/%y")
                except (ValueError, TypeError):
                    formatted_date_mdy = str(raw_bullet_date)

            safe_source = html.escape(source)
            safe_formatted_date_mdy = html.escape(formatted_date_mdy)

            if url and url != '#':
                safe_url = html.escape(url.replace('"', '"'))
                if not safe_url.startswith(('http://', 'https://')):
                    safe_url = 'http://' + safe_url
                safe_link_text = safe_formatted_date_mdy
                citation = f'[{safe_source}, <a href="{safe_url}" target="_blank" rel="noopener noreferrer"><em>{safe_link_text}</em></a>] ({type_input})'
            else:
                citation = f'[{safe_source}, {safe_formatted_date_mdy}] ({type_input})'

            title_cased_headline = apply_strict_title_case_every_word(headline)
            safe_headline = html.escape(title_cased_headline)
            safe_body = html.escape(formatted_body)

            html_parts.append("<div class=\"bullet\">")
            html_parts.append(f"<p><b>{safe_headline}</b> \"{safe_body}\" {citation}</p>")
            html_parts.append("</div>")
    else:
        html_parts.append("<p>No relevant bullets were extracted. Using Bullets</p>")
    html_parts.append("</div>")

    # --- Full Transcript Section ---
    html_parts.append("<h3>TRANSCRIPT</h3>")
    html_parts.append(transcript_text if transcript_text else "Transcript unavailable.")
    
    # --- Closing HTML ---
    html_parts.append("</div>")
    if html_or_docx == "html":
        html_parts.append("</body></html>")

    logging.info("HTML report string generated.")
    return "\n".join(html_parts)
