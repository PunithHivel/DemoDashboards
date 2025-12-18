from pydantic import BaseModel


class PullRequestImportResponse(BaseModel):
    rows_received: int
    rows_inserted: int
    rows_skipped: int


EXPECTED_COLUMNS = [
    "id",
    "actualpullrequestid",
    "title",
    "authorid",
    "createdon",
    "description",
    "destinationbranch",
    "sourcebranch",
    "firstcommitid",
    "sourcecommitid",
    "destinationcommitid",
    "state",
    "repoid",
    "linesadded",
    "linesremoved",
    "htmllink",
    "commentcount",
    "commitscount",
    "modifiedfilescount",
    "updatedon",
    "mergecommit",
    "mergedby",
    "approvedby",
    "mergedon",
    "declinedon",
    "approvedon",
    "firstcommittedon",
    "committoopenduration",
    "opentoreviewduration",
    "reviewedtoapprovedduration",
    "reviewedtomergedduration",
    "approvedtomergedduration",
    "reviewedtodeclineduration",
    "opentodeclineduration",
    "opentomergedduration",
    "cycletimeduration",
    "deploytimeduration",
    "cycletimeoverflow",
    "declinedby",
    "remark",
    "originalauthorid",
    "originalapprovedby",
    "originalfirstreviewedby",
    "originaldeclinedby",
    "processed",
    "hotfixpr",
    "reviewbranchpr",
    "releasebranchpr",
    "excludepr",
    "flashyreviewedpr",
    "organizationid",
    "workspaceid",
    "userintegrationid",
    "reviewcyclecount",
    "opentofirstcommentduration",
    "firstcommenttoapproved",
]

REQUIRED_COLUMNS = {
    "id",
    "actualpullrequestid",
    "authorid",
    "createdon",
    "repoid",
    "organizationid",
    "workspaceid",
}

TIMESTAMP_COLUMNS = {
    "createdon",
    "updatedon",
    "mergedon",
    "declinedon",
    "approvedon",
    "firstcommittedon",
}

FLOAT_COLUMNS = {
    "committoopenduration",
    "opentoreviewduration",
    "reviewedtoapprovedduration",
    "reviewedtomergedduration",
    "approvedtomergedduration",
    "reviewedtodeclineduration",
    "opentodeclineduration",
    "opentomergedduration",
    "cycletimeduration",
    "deploytimeduration",
    "opentofirstcommentduration",
    "firstcommenttoapproved",
}

INT_COLUMNS = {
    "id",
    "actualpullrequestid",
    "authorid",
    "repoid",
    "linesadded",
    "linesremoved",
    "commentcount",
    "commitscount",
    "modifiedfilescount",
    "mergedby",
    "approvedby",
    "declinedby",
    "originalauthorid",
    "originalapprovedby",
    "originalfirstreviewedby",
    "originaldeclinedby",
    "organizationid",
    "workspaceid",
    "userintegrationid",
    "reviewcyclecount",
}

BOOL_COLUMNS = {
    "cycletimeoverflow",
    "processed",
    "hotfixpr",
    "reviewbranchpr",
    "releasebranchpr",
    "excludepr",
    "flashyreviewedpr",
}
