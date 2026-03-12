from google.cloud.firestore_v1.base_query import FieldFilter
def check_if_user_is_registered_for_event(event_registrations_collection,project_map,user_email: str, event_id: str):
    """
    
    Check if a user is registered for an event using the email and event id

    Parameters:
    - user_email: The user's email address.
    - event_id: The unique ID of the event.

    Only call this tool when BOTH user_email and event_id are known.

    Returns:
    - True if the user is registered for the event, False otherwise.
    
    """
    
    docs = (
        event_registrations_collection.where(filter=FieldFilter("userEmail", "==", user_email))
        .where(filter=FieldFilter("event_id", "==", event_id))
        .limit(1)
        .get()
    )
    return {"success": True, "message": "User is registered for this event", "event_id": event_id} if len(docs) > 0 else {"success": True, "message": "User is not registered for this event", "event_id": event_id}


def get_user_registered_events(event_registrations_collection,project_map,user_email: str) -> list:
    """
    Get the events a user is registered for using the user email

    Parameters:
    - user_email: The user's email address.

    Returns:
    - A list of events the user is registered for.
    
    """
    docs = event_registrations_collection.where(
        filter=FieldFilter("userEmail", "==", user_email)
    ).get()
    result = []
    for doc in docs:
        data = doc.to_dict() or {}
        event_id = data.get("event_id") or data.get("eventId")
        if not event_id:
            continue
        event_info = {"event_id": event_id, "event_name": data.get("event_name")}
        # Enrich with project/event details if available
        project_snap = project_map.get(event_id)
        if project_snap:
            event_data = project_snap.to_dict() or {}
            event_info["event_name"] = event_info.get("event_name") or event_data.get("name")
            event_info["start_date"] = event_data.get("startDate")
            event_info["end_date"] = event_data.get("endDate")
            event_info["venue"] = event_data.get("venue")
        result.append(event_info)
    return result



def register_user_for_event(event_registrations_collection,project_map,user_email: str, event_id: str) -> bool:
    """
    Register a user for an event

    Parameters:
    - user_email: The user's email address.
    - event_id: The unique ID of the event.

    Returns:
    - A message indicating the result of the registration.

    Only call this tool when BOTH user_email and event_id are known.
    """
    # Avoid duplicate registration
    existing = (
        event_registrations_collection.where(filter=FieldFilter("userEmail", "==", user_email))
        .where(filter=FieldFilter("event_id", "==", event_id))
        .limit(1)
        .get()
    )
    if len(existing) > 0:
        return {"success": True, "message": "User is already registered for this event", "event_id": event_id}  
    # Get event name from project_map if available
    event_name = None
    project_snap = project_map.get(event_id)
    if project_snap:
        event_name = (project_snap.to_dict() or {}).get("name")
    reg_doc = {
        "userEmail": user_email,
        "event_id": event_id,
        "event_name": event_name,
    }
    event_registrations_collection.add(reg_doc)
    return {"success": True, "message": "User successfully registered for event", "event_id": event_id}

