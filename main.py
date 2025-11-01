from bluefolder_api import get_todays_tickets
from routing import get_route

# TEMP hardcoded user ID and dummy addresses
USER_ID = "12345"  # Replace with actual user ID
dummy_addresses = [
    "123 Main St, City, State",
    "456 Elm St, City, State",
    "789 Oak St, City, State"
]

if __name__ == "__main__":
    #tickets = get_todays_tickets(USER_ID)
    directions = get_route(dummy_addresses)

    if directions:
        for step in directions[0]['legs']:
            print(f"Route: {step['start_address']} to {step['end_address']}")
    else:
        print("Not enough stops for a route.")
