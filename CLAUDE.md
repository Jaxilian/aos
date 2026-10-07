# AOS

A Linux desktop OS built with Buildroot: this directory is an unmodified
Buildroot checkout and everything AOS lives under `br2ext/`. The apps
(compositor, shell, Software, Settings, installer, ...) are separate
repositories pinned here by commit.

Read the workflow before doing anything else; it says where things are,
how to build, test in QEMU, release, and run the hardware round:

@WORKFLOW.md

Then read `TODO.md` (state of the work, open decisions) and the top of
`TEST.md` (what the user is testing on the stick).
