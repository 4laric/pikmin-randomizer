# Source content for the authored Hole of Beasts scene

Run `python -m experimental.pikmin2_beasts_content --iso <local US ISO> --catalog <catalog.json> --output <new directory>`. Add `--assets <P1 assets> --assembly <Beasts assembly> --pod <Pod import>` to prepare a private native stage.

The importer verifies the cave definition against the catalog source hash and reads the US treasure config and archive directly. The floor-one treasure is `juji_key_fc`: 100 Pokos, five carrying strength, ten attachment slots. It converts the actual model, bakes its bottom to floor height, records source and output hashes, and replaces the borrowed Citrus model and economy in a fresh private stage. The chosen east-room center remains an authored engineering placement; source generation has not selected it.

Floor one contains four UjiB and three distinct UjiA definition rows of two each (six total). Clover has target count four, Tukushi two, and KareOoinu_s two. Definition IDs preserve the separate UjiA rows. All five enemy/plant species remain explicitly unsupported in this stage; none are replaced with P1 actors. There are no gate or cap definitions. The source disables geyser and clogged-hole flags. A descent is required on this nonfinal floor, but selected hole placement and lifecycle are not implemented here.

Four focused tests cover distinct row IDs, source population and treasure rejection, and independent exit flags. Two actual US-disc imports produce byte-identical metadata and models. The model contains 138 vertices and 222 triangles. Local preparation is at `output/p2-beasts-content-batch/verified/runs/bf58a441f75a41a2a6cda1614f2f19c8`.

Do not run the inherited second-floor native acceptance fixture unchanged: it asserts the old Citrus value of 180. This 100-Poko source-content stage is preparation-only pending a configurable native assertion. Its manifest leaves native validation false. No full roster, retail generation, complete floor, or native hauling acceptance is claimed. Assets stay local; no native code, shared converter or earlier fixture files are modified.
