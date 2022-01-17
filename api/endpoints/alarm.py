from datetime import datetime
from typing import Optional, List
from fastapi import Depends, Body, Path, Query
from fastapi.security import HTTPBasicCredentials
from starlette.responses import Response

import common
import models.alarm
import models.common
from I4cAPI import I4cApiRouter
from common import CredentialsAndFeatures
from common.exceptions import I4cClientNotFound, I4cClientError
from models import CommonStatusEnum
import pytz

router = I4cApiRouter(include_path="/alarm")


@router.put("/defs/{name}", response_model=models.alarm.AlarmDef, operation_id="alarm_set",
            summary="Update alarm definition.")
async def alarmdef_put(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("put/alarm/defs/{name}")),
    name: str = Path(..., title="Identifier name."),
    alarm: models.alarm.AlarmDefIn = Body(...),
):
    """Create or update alarm definition."""
    return await models.alarm.alarmdef_put(credentials, name, alarm)


@router.get("/defs/{name}", response_model=models.alarm.AlarmDef, operation_id="alarm_get",
            summary="Retrieve alarm definition.")
async def alarmdef_get(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/alarm/defs/{name}")),
    name: str = Path(..., title="Identifier name."),
):
    """Retrieve definition of alarm."""
    res = await models.alarm.alarmdef_get(credentials, name)
    if res is None:
        raise I4cClientNotFound("No record found")
    return res


@router.get("/defs", response_model=List[models.alarm.AlarmDef], operation_id="alarm_list",
            summary="List alarm definitions.")
async def alarmdef_list(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("get/alarm/defs")),
    name_mask: Optional[List[str]] = Query(None, title="Search phrase for the name."),
    report_after: Optional[datetime] = Query(None, title="timestamp", description="eg.: 2021-08-15T15:53:11.123456Z"),
    subs_status: Optional[CommonStatusEnum] = Query(None, title="Has a subscriber with the status."),
    subs_method: Optional[models.alarm.AlarmMethod] = Query(None, title="Has a subscriber via this method."),
    subs_address: Optional[str] = Query(None, title="Has a subscriber with this exact address."),
    subs_address_mask: Optional[List[str]] = Query(None, title="Has a subscriber with address matching this search expression."),
    subs_user: Optional[str] = Query(None, title="User subscribing."),
    subs_user_mask: Optional[List[str]] = Query(None, title="Search expression for a subscriber user name.")
):
    """List alarm definitions."""
    return await models.alarm.alarmdef_list(credentials, name_mask, report_after,
                                            subs_status, subs_method, subs_address, subs_address_mask, subs_user, subs_user_mask)


@router.get("/subsgroupusage", response_model=List[models.alarm.SubsGroupsUser], operation_id="alarm_subsgroupusage",
            summary="List subscription user memberships.", features=["any user"])
async def subsgroupsusage_list(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/alarm/subsgroupusage", ask_features=["any user"])),
        user: Optional[str] = Query(None, title="Filter for this user. If not self or not specified, special privilege required.")):
    """List subscription groups."""
    return await models.alarm.subsgroupsusage_list(credentials, user)


@router.get("/subsgroups/{name}", response_model=models.alarm.SubsGroups, operation_id="alarm_subsgroup_members_get",
            summary="Get subscription group with members.")
async def subsgroup_members_get(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/alarm/subsgroups/{name}")),
        name: str = Path(..., title="Filter for this group.")):
    """Get subscription group with members."""
    res = await models.alarm.subsgroup_members(credentials, group=name)
    if len(res) > 0:
        return res[0]
    raise I4cClientNotFound("No record found")


@router.get("/subsgroups", response_model=List[models.alarm.SubsGroups], operation_id="alarm_subsgroup_members_list",
            summary="List subscription groups.")
async def subsgroup_members_list(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/alarm/subsgroups")),
        user: Optional[str] = Query(None, title="Filter for user."),
        group: Optional[str] = Query(None, title="Filter for group.")):
    """List subscription group with members."""
    return await models.alarm.subsgroup_members(credentials, user, group)


@router.put("/subsgroups/{name}", status_code=201, response_class=Response, operation_id="alarm_subsgroup_members_put",
            summary="Update alarm subgroup member definition.")
async def subsgroup_members_put(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("put/alarm/subsgroups/{name}")),
    name: str = Path(..., title="Identifier name."),
    sub_groups_in: models.alarm.SubsGroupsIn = Body(...),
):
    """Update alarm subgroup member definition."""
    await models.alarm.subsgroup_members_put(credentials, name, sub_groups_in)


@router.delete("/subsgroups/{name}", status_code=204, response_class=Response, operation_id="alarm_subsgroup_delete",
               summary="Delete alarm subgroup.")
async def subsgroup_delete(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("delete/alarm/subsgroups/{name}")),
    name: str = Path(..., title="Group name."),
    forced: Optional[bool] = Query(False, title="Delete group with members, but groups used in alarms cannot be deleted")
):
    """Delete alarm subgroup."""
    await models.alarm.subsgroup_delete(credentials, name, forced)


@router.get("/subs", response_model=List[models.alarm.AlarmSub], operation_id="alarm_subscribers",
            summary="List subscribers.", features=["any user"])
async def alarmsub_list(
        credentials: CredentialsAndFeatures = Depends(common.security_checker("get/alarm/subs", ask_features=["any user"])),
        id: Optional[str] = Query(None, title="Identifier."),
        group: Optional[str] = Query(None, title="Member of the group."),
        group_mask: Optional[List[str]] = Query(None, title="Search phrase for a group name."),
        user: Optional[str] = Query(None, title="Identifier of the user."),
        user_name: Optional[str] = Query(None, title="Exact user name."),
        user_name_mask: Optional[List[str]] = Query(None, title="Search phrase for user name."),
        method: Optional[models.alarm.AlarmMethod] = Query(None, title="Method."),
        status: Optional[CommonStatusEnum] = Query(None, title="Status."),
        address: Optional[str] = Query(None, title="Exact address."),
        address_mask: Optional[List[str]] = Query(None, title="Search phrase for address."),
        alarm: Optional[str] = Query(None, title="Subscribes to this alarm.")):
    """Get the list of subscribers"""
    return await models.alarm.alarmsub_list(credentials, id, group, group_mask, user, user_name, user_name_mask,
                                            method, status, address, address_mask, alarm)


@router.get("/subs/{id}", response_model=models.alarm.AlarmSub, operation_id="alarm_subscriber",
            summary="Retrieve subscriber.", features=["any user"])
async def alarmsub_get(
        credentials: CredentialsAndFeatures = Depends(common.security_checker("get/alarm/subs/{id}", ask_features=["any user"])),
        id: int = Path(...)):
    """Retrieve an alarm subscriber."""
    res = await models.alarm.alarmsub_list(credentials, id=id)
    if len(res) > 0:
        res = res[0]
        if (credentials.user_id != res.user) and ("any user" not in credentials.info_features):
            raise I4cClientError("Unauthorized to access other users' subscriptions.")
        return res
    raise I4cClientNotFound("No record found")


@router.post("/subs", response_model=models.alarm.AlarmSub, operation_id="alarm_subscribe",
             summary="Create subscriber.", features=["any user"])
async def post_alarmsub(
    credentials: CredentialsAndFeatures = Depends(common.security_checker("post/alarm/subs", ask_features=["any user"])),
    alarmsub: models.alarm.AlarmSubIn = Body(...),
):
    """Create a subscriber that can receive alarm notifications."""
    return await models.alarm.post_alarmsub(credentials, alarmsub)


@router.patch("/subs/{id}", response_model=models.common.PatchResponse, operation_id="alarm_subscription_update",
              summary="Update subscriber.", features=["any user"])
async def patch_alarmsub(
    credentials: CredentialsAndFeatures = Depends(common.security_checker("patch/alarm/subs/{id}", ask_features=["any user"])),
    id: int = Path(...),
    patch: models.alarm.AlarmSubPatchBody = Body(...),
):
    """Change a subscriber if conditions are met."""
    return await models.alarm.patch_alarmsub(credentials, id, patch)


@router.post("/events/check", response_model=List[models.alarm.AlarmEventCheckResult], operation_id="alarm_check",
             summary="Check for alarm conditions.", features=['noaudit'])
async def check_alarmevent(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("post/alarm/events/check", ask_features=['noaudit'])),
    alarm: Optional[str] = Query(None, title="Only check this alarm."),
    max_count: Optional[int] = Query(None, title="Stop after creating this many events."),
    noaudit: bool = Query(False, title="Don't write audit record. Requires special privilege.")
):
    """Check alarms and create events if an alarm state is detected."""
    def hun_tz(dt):
        tz = pytz.timezone("Europe/Budapest")
        return tz.localize(dt)

    # return await models.alarm.check_alarmevent(credentials, alarm, max_count, override_last_check=hun_tz(datetime(2021,10,27,13,21)), override_now=hun_tz(datetime(2021,10,27,13,30)))
    return await models.alarm.check_alarmevent(credentials, alarm, max_count)


@router.get("/events", response_model=List[models.alarm.AlarmEvent], operation_id="alarm_events",
            summary="List alarm events.")
async def alarmevent_list(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/alarm/events")),
        id: Optional[str] = Query(None, title="."),
        alarm: Optional[str] = Query(None, title="Exact alarm name."),
        alarm_mask: Optional[List[str]] = Query(None, title="Alarm name search expression."),
        user: Optional[str] = Query(None, title="User identifier."),
        user_name: Optional[str] = Query(None, title="Exact user name."),
        user_name_mask: Optional[List[str]] = Query(None, title="User name search expression."),
        before: Optional[datetime] = Query(None, title="Created before, iso timestamp."),
        after: Optional[datetime] = Query(None, title="Created after, iso timestamp."),
):
    """List alarm events."""
    return await models.alarm.alarmevent_list(credentials, id, alarm, alarm_mask, user, user_name, user_name_mask, before, after)


@router.get("/events/{id}", response_model=models.alarm.AlarmEvent, operation_id="alarm_event",
            summary="Retrieve alarm event.")
async def alarmevent_get(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/alarm/events/{id}")),
        id: int = Path(...)):
    """Retrieve an alarm event."""
    res = await models.alarm.alarmevent_list(credentials, id=id)
    if len(res) > 0:
        return res[0]
    raise I4cClientNotFound("No record found")


@router.get("/recips", response_model=List[models.alarm.AlarmRecip], operation_id="alarm_recips",
            summary="List alarm recipients.", features=['noaudit'])
async def alarmrecips_list(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/alarm/recips", ask_features=['noaudit'])),
        id: Optional[str] = Query(None),
        alarm: Optional[str] = Query(None, title="Exact alarm name."),
        alarm_mask: Optional[List[str]] = Query(None, title="Alarm name search expression."),
        event: Optional[int] = Query(None, title="Event id."),
        user: Optional[str] = Query(None, title="User identifier."),
        user_name: Optional[str] = Query(None, title="Exact user name."),
        user_name_mask: Optional[List[str]] = Query(None, title="User name search expression."),
        user_status: Optional[CommonStatusEnum] = Query(None, title="User status."),
        method: Optional[models.alarm.AlarmMethod] = Query(None, title="Notification method."),
        status: Optional[models.alarm.AlarmRecipientStatus] = Query(None, title="Notification status."),
        noaudit: bool = Query(False, title="Don't write audit record. Requires special privilege.")
):
    """List the recipients of an alarm event."""
    return await models.alarm.alarmrecips_list(credentials, id, alarm, alarm_mask, event,
                                               user, user_name, user_name_mask, user_status, method, status)


@router.get("/recips/{id}", response_model=models.alarm.AlarmRecip, operation_id="alarm_recip",
            summary="Retrieve alarm recipient.")
async def alarmrecips_get(
        credentials: HTTPBasicCredentials = Depends(common.security_checker("get/alarm/recips/{id}")),
        id: int = Path(...)):
    """Retrieve a recipient of an alarm event."""
    res = await models.alarm.alarmrecips_list(credentials, id=id)
    if len(res) > 0:
        return res[0]
    raise I4cClientNotFound("No record found")


@router.patch("/recips/{id}", response_model=models.common.PatchResponse, operation_id="alarm_recip_update",
              summary="Update alarm recipient.")
async def patch_alarmrecips(
    credentials: HTTPBasicCredentials = Depends(common.security_checker("patch/alarm/recips/{id}")),
    id: int = Path(...),
    patch: models.alarm.AlarmRecipPatchBody = Body(...),
):
    """Change a recipient of an alarm event if conditions are met."""
    return await models.alarm.patch_alarmrecips(credentials, id, patch)
