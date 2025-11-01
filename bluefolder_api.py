# bluefolder_api.py

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("BLUEFOLDER_API_KEY")
ACCOUNT_NAME = os.getenv("BLUEFOLDER_ACCOUNT_NAME")

# Example base URL — adjust to match documentation
BASE_URL = f"https://app.bluefolder.com/api/2.0/json/"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "ApiKey": API_KEY,
}


def _make_request(method: str, params: dict = None):
    if not API_KEY or not ACCOUNT_NAME:
        raise EnvironmentError(
            "Missing BLUEFOLDER_API_KEY or BLUEFOLDER_ACCOUNT_NAME in .env"
        )

    payload = {"method": method, "params": params or {}}
    response = requests.post(BASE_URL, headers=HEADERS, json=payload)
    response.raise_for_status()
    return response.json()


# Service Requests / Tickets
def list_service_requests(filter_params: dict = None):
    """
    List service requests. Accepts optional filter parameters (e.g., date range, assigned technician).
    """
    return _make_request("serviceRequest.list", {"filter": filter_params or {}})


def get_service_request(ticket_id: int):
    """
    Get the details of a specific service request by ID.
    """
    return _make_request("serviceRequest.get", {"serviceRequestID": ticket_id})


# Users (Technicians)
def list_users(filter_params: dict = None):
    """
    List users (technicians or other staff). Accepts filter params.
    """
    return _make_request("user.list", {"filter": filter_params or {}})


def get_user(user_id: int):
    """
    Get details for a specific user.
    """
    return _make_request("user.get", {"userID": user_id})


# Customer Locations (addresses)
def list_customer_locations(filter_params: dict = None):
    """
    List customer locations; useful to get addresses tied to service requests.
    """
    return _make_request("customerLocation.list", {"filter": filter_params or {}})


def get_customer_location(location_id: int):
    """
    Get details of a specific location (including address data).
    """
    return _make_request("customerLocation.get", {"customerLocationID": location_id})


# Assignments / Appointments (if needed)
def list_appointments(filter_params: dict = None):
    """
    List appointments or scheduled blocks (if your workflow uses them).
    """
    return _make_request("appointment.list", {"filter": filter_params or {}})


def get_appointment(appointment_id: int):
    """
    Get the details of a specific appointment.
    """
    return _make_request("appointment.get", {"appointmentID": appointment_id})
