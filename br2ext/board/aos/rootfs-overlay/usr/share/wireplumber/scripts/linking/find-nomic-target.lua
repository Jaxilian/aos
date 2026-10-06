-- AOS: a capture stream from a client without the microphone permission
-- (access "nomic", the pipewire-0-nomic socket or the pulse nomic
-- address) gets no target. The client hears an error and the node goes,
-- so a program sees "cannot open the microphone", not silence. Playback
-- streams pass through to the usual hooks.

lutils = require ("linking-utils")
log = Log.open_topic ("s-linking")

SimpleEventHook {
  name = "linking/find-nomic-target",
  before = "linking/find-defined-target",
  interests = {
    EventInterest {
      Constraint { "event.type", "=", "select-target" },
    },
  },
  execute = function (event)
    local source, om, si, si_props, si_flags, target =
        lutils:unwrap_select_target_event (event)

    if target then
      return
    end
    local class = si_props ["media.class"] or ""
    if not class:find ("^Stream/Input") then
      return
    end
    local node = si:get_associated_proxy ("node")
    if not node then
      return
    end
    local client_id = node.properties ["client.id"]
    if not client_id then
      return
    end
    local clients_om = source:call ("get-object-manager", "client")
    local client = clients_om:lookup {
      Constraint { "bound-id", "=", client_id, type = "gobject" }
    }
    if not client then
      return
    end
    local access = client.properties ["pipewire.access.effective"]
        or client.properties ["pipewire.access"]
    if access ~= "nomic" then
      return
    end

    log:warning (si, string.format ("microphone is off for client %s (%s): capture stream %s refused",
        client_id, tostring (client.properties ["application.name"]), tostring (si_props ["node.name"])))
    lutils.sendClientError (event, node, -13, "the microphone is off for this program (Software, Permissions)")
    node:request_destroy ()
    event:stop_processing ()
  end
}:register ()
