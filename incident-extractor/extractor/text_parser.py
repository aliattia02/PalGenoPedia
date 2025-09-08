import re
from datetime import datetime


def extract_incidents_from_text(text):
    """
    Extract potential incidents from provided text
    """
    # This is a simplified version - you would implement more sophisticated NLP here
    incidents = []

    # Split text into paragraphs
    paragraphs = text.split('\n\n')

    for paragraph in paragraphs:
        if len(paragraph.strip()) < 30:
            continue  # Skip short paragraphs

        # Look for potential incidents - simplified detection
        if any(keyword in paragraph.lower() for keyword in
               ['killed', 'died', 'wounded', 'injured', 'attack', 'strike', 'bomb',
                'airstrike', 'hospital', 'school', 'refugee', 'hunger', 'starvation']):

            # Extract date (very simplified)
            date_match = re.search(r'\d{1,2} [A-Za-z]+ \d{4}', paragraph)
            date = date_match.group(0) if date_match else datetime.now().strftime("%d %B %Y")

            # Extract location (very simplified)
            locations = ["Gaza City", "Rafah", "Khan Younis", "Jabalia", "Beit Lahiya", "Beit Hanoun"]
            location = None
            for loc in locations:
                if loc.lower() in paragraph.lower():
                    location = loc
                    break

            # Determine incident type
            incident_type = "casualties"  # default
            if "hunger" in paragraph.lower() or "starvation" in paragraph.lower():
                incident_type = "hunger"
            elif "water" in paragraph.lower():
                incident_type = "water"
            elif "aid" in paragraph.lower() or "humanitarian" in paragraph.lower():
                incident_type = "aid"
            elif "hospital" in paragraph.lower() or "school" in paragraph.lower():
                incident_type = "infrastructure"

            # Create incident object
            incident = {
                "type": incident_type,
                "description": paragraph.strip(),
                "date": date,
                "location": location
            }

            # Try to extract casualty numbers
            casualties_match = re.search(
                r'(\d+) (people|persons|civilians|children|women) (killed|wounded|injured|died)',
                paragraph, re.IGNORECASE)
            if casualties_match:
                incident["casualties"] = casualties_match.group(0)

            incidents.append(incident)

    return incidents