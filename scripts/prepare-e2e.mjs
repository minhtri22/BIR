import { rm, mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';

const tmpDir = resolve('test-tmp');
await mkdir(tmpDir, { recursive: true });
await rm(resolve(tmpDir, 'e2e.db'), { force: true });
await rm(resolve(tmpDir, 'e2e.db-shm'), { force: true });
await rm(resolve(tmpDir, 'e2e.db-wal'), { force: true });
await rm(resolve(tmpDir, 'e2e-artifacts'), { force: true, recursive: true });
