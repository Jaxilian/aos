# What apm installs. /etc/profile sets PATH to /usr/bin and then sources
# this, so the store's symlink farm goes in front of it; the desktop gets
# the same two variables from the ade.service drop-in, since a system unit
# reads neither this file nor environment.d.
#
# Guarded, because a login subshell sources /etc/profile again and would
# otherwise prepend a second copy each time.
case ":$PATH:" in
	*":/opt/apm/bin:"*) ;;
	*) export PATH="/opt/apm/bin:$PATH" ;;
esac
case ":${XDG_DATA_DIRS:-}:" in
	*":/opt/apm/exports/share:"*) ;;
	*) export XDG_DATA_DIRS="/opt/apm/exports/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}" ;;
esac
