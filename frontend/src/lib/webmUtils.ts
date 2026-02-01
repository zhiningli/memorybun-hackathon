/**
 * WebM Container Parsing Utilities
 * 
 * These utilities help extract the init segment (EBML header + Segment info + Tracks)
 * from WebM files. This is necessary because MediaRecorder's timeslice feature only
 * includes the init segment in chunk 0 - subsequent chunks are continuation data
 * that ffmpeg cannot parse without the headers.
 * 
 * WebM Structure:
 * ┌─────────────────────────────┐
 * │ EBML Header (0x1A45DFA3)   │
 * ├─────────────────────────────┤
 * │ Segment (0x18538067)       │
 * │   ├─ SeekHead              │
 * │   ├─ SegmentInfo           │  ← Init Segment
 * │   ├─ Tracks                │
 * │   └─ Cluster (0x1F43B675)  │  ← Media data starts here
 * └─────────────────────────────┘
 */

/**
 * Find the byte offset of the first Cluster element in WebM data.
 * The Cluster element ID is 0x1F43B675 (4 bytes).
 * 
 * @param data - Uint8Array containing WebM data
 * @returns Byte offset of first Cluster, or -1 if not found
 */
export function findClusterOffset(data: Uint8Array): number {
    // Cluster Element ID: 0x1F 0x43 0xB6 0x75
    // We scan for this 4-byte pattern to find where media data starts
    const len = data.length - 3;

    for (let i = 0; i < len; i++) {
        if (
            data[i] === 0x1F &&
            data[i + 1] === 0x43 &&
            data[i + 2] === 0xB6 &&
            data[i + 3] === 0x75
        ) {
            return i;
        }
    }

    return -1;
}

/**
 * Extract the init segment from a WebM blob.
 * The init segment contains everything before the first Cluster:
 * EBML header, Segment element start, SeekHead, SegmentInfo, and Tracks.
 * 
 * This init segment must be prepended to subsequent chunks to make them
 * valid, standalone WebM files that ffmpeg can parse.
 * 
 * @param blob - Blob containing WebM data (typically chunk 0 from MediaRecorder)
 * @returns ArrayBuffer containing the init segment
 * @throws Error if Cluster element is not found
 */
export async function extractInitSegment(blob: Blob): Promise<ArrayBuffer> {
    const buffer = await blob.arrayBuffer();
    const data = new Uint8Array(buffer);
    const clusterOffset = findClusterOffset(data);

    if (clusterOffset <= 0) {
        throw new Error(
            "Could not find Cluster element in WebM data. " +
            "The blob may not be a valid WebM file or may be too small."
        );
    }

    // Return everything before the first Cluster
    // Using slice() creates a copy, which is what we want for caching
    return buffer.slice(0, clusterOffset);
}

/**
 * Prepend the init segment to a WebM chunk blob.
 * This creates a new Blob that ffmpeg can parse independently.
 * 
 * @param initSegment - ArrayBuffer containing the init segment from chunk 0
 * @param chunkBlob - Blob containing the continuation chunk data
 * @returns New Blob with init segment prepended
 */
export function prependInitSegment(
    initSegment: ArrayBuffer,
    chunkBlob: Blob
): Blob {
    return new Blob([initSegment, chunkBlob], { type: "audio/webm" });
}
