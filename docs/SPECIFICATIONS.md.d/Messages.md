    ## Addresses
    From: :session:<session-id>

    To:
    :session:<session-id> (requires manual auth)
    :topic:<topic-name> (fixed list,need daemon sig)

    ## Fixed list of messages

    Subjet:<type> see blow

    Agent status tracking (project)
    - orchard:agent:status (freetext describing in one word the agent activity)
    - orchard:agent:outcome:success|fail

    Agent lifeccycle tracking (sidebar etc) (gobal)
    - orchard:agent:lifecycle:starting|started|stopping|stopped
    

    subagents broadcast global
    - orchard:agent:delegation:begin:<subagentNae / session-id>
    - orchard:agent:delegation:end:<subagent / session-id>

    PubSub (global):
    - orchard:bus:subscribe:<topic-name> (scriptcreates specific folder for the agent and imonitor)
    - orchard:bus:unsubscribe:<topic-name> (scriptdeletes it all anddiscard remaning content)


    Session message (content in body)

    Relaying operator intructions
    - orchard:operator:message:todo|instructions|request|response|content

    Relaying agent intructin
    - orchard:agent:message:request|response|conent

Internal messages (session messages)

Getting the immutable information about a session
    - orchard:identity (request/response)

Getting the mutable information about a session
    - orchard:status (request/response)