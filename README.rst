=========================================
Thonny — Neutral Edition
=========================================

.. image:: https://img.shields.io/badge/based_on-v5.0.0-blue
   :alt: Based on Thonny 5.0.0

Open Source has nothing to do with politics.

This is a `fork <https://github.com/GGnqfh/thonny-neutral>`_ of `thonny/thonny <https://github.com/thonny/thonny>`_ — a popular Python IDE for beginners.
The only difference from upstream is the **removal of all Ukraine-related GUI elements**.
Everything else is kept in sync with upstream releases via a fully automated pipeline.

If you like Thonny but prefer a politically neutral toolbar, this is for you.


What's different
================

======================= ============== ======================
Item                    Upstream       thonny-neutral
======================= ============== ======================
"Support Ukraine" button ✅ toolbar     ❌ removed
Status bar label        ✅ shown       ❌ removed
Ukraine flag images     ✅ shipped     ❌ deleted
Ukraine links in README ✅ present     ❌ removed
Changelog Ukraine entry ✅ present     ❌ removed
Code signing (Windows)  ✅ signed      ❌ disabled
All IDE features        ✅             ✅ identical
======================= ============== ======================

**That's it.** One purpose, one change, zero feature modifications.


How it works — fully automated
===============================

This fork runs on two GitHub Actions workflows that require **zero human intervention**:

1. Sync (`.github/workflows/sync-upstream.yml`)
   - Runs daily at 06:00 UTC, or can be triggered manually
   - Fetches all tags from `thonny/thonny`
   - Compares against existing ``*-neutral`` tags to find unsynced versions
   - For each new version, runs `tools/sync_upstream.py` which:

     #. Creates a branch from the upstream tag
     #. Deletes Ukraine flag images (``Ukraine.png``, ``Ukraine48.png``, etc.)
     #. Patches ``workbench.py`` — removes the toolbar button, status bar, and helper methods
     #. Patches ``pi/__init__.py`` — removes Ukraine image mappings
     #. Patches ``README.rst`` — removes the flag image and support link
     #. Patches ``CHANGELOG.rst`` — removes the Ukraine-related entry
     #. Disables code signing in ``inno_setup.iss``
     #. Scans the entire codebase for any remaining Ukraine references
     #. Commits, tags as ``vX.Y.Z-neutral``, and pushes

2. Build (`.github/workflows/build.yml`)
   - Triggered automatically when a ``v*-neutral`` tag is pushed
   - Builds a Python wheel, Windows installer (.exe), and macOS installers for both Intel and Apple Silicon
   - Creates a GitHub Release with all artifacts attached

The result: every time upstream releases a new version, a matching ``*-neutral`` release is published automatically within hours.


Background
==========

Multiple users have asked upstream to make the Ukraine button optional or removable (`#2572 <https://github.com/thonny/thonny/issues/2572>`_, `#3424 <https://github.com/thonny/thonny/issues/3424>`_, `#3631 <https://github.com/thonny/thonny/issues/3631>`_, `#3825 <https://github.com/thonny/thonny/issues/3825>`_).
All were closed as "not planned". Some users — particularly educators in countries with strict neutrality laws — need Thonny without political messaging.
This fork exists to fill that gap.


Contributors
=============

Contributions are welcome! See upstream's `CONTRIBUTING.rst <https://github.com/thonny/thonny/blob/master/CONTRIBUTING.rst>`_.

This fork accepts only changes that help maintain parity with upstream or improve the automation scripts.
Feature requests or changes that deviate from upstream are out of scope.


Sponsors
=========

You can sponsor development of Thonny by sending a donation to Thonny's main author Aivar Annamaa:
https://github.com/thonny/thonny/wiki/Sponsors
