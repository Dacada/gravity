#ifndef GRAVITY_H
#define GRAVITY_H

#include <stdbool.h>
#include <stddef.h>

/*
 * Custom allocator interface used by the gravity system.
 *
 * All dynamic memory used internally by a gravity instance is obtained
 * exclusively through this allocator once provided at initialization.
 *
 * Assumptions:
 * - malloc(size) behaves like standard malloc and returns NULL on failure.
 * - realloc(ptr, size) behaves like standard realloc:
 *     * realloc(NULL, size) is equivalent to malloc(size)
 *     * realloc(ptr, 0) may return NULL and free ptr
 * - free(ptr) safely accepts NULL.
 *
 * If any of these assumptions do not hold, behavior is undefined.
 */
struct allocator_info {
  void *(*malloc)(size_t);
  void *(*realloc)(void *, size_t);
  void (*free)(void *);
};

/*
 * Opaque handle identifying an entity in the simulation.
 *
 * slot_idx indexes into the internal slot array.
 * generation is used to detect stale handles after deletion and reuse.
 *
 * A handle is valid if and only if:
 * - slot_idx refers to an occupied slot
 * - generation matches the generation stored in that slot
 *
 * Handles are cheap to copy and compare by value.
 */
struct gravity_handle {
  size_t slot_idx;
  size_t generation;
};

/*
 * User-facing representation of an entity.
 *
 * This struct is used for creation and retrieval only. Internally,
 * entities are stored in a structure-of-arrays layout for performance.
 *
 * Units and coordinate system are user-defined but must be consistent.
 */
struct gravity_entity {
  double px;   /* position x */
  double py;   /* position y */
  double vx;   /* velocity x */
  double vy;   /* velocity y */
  double mass; /* mass (must be non-negative; behavior otherwise undefined) */
};

/*
 * Information about entity merges that occurred during a physics update.
 *
 * For each merge i in [0, nmerges):
 * - merge1[i] and merge2[i] are the handles of the entities that were removed
 * - into[i] is the handle of the entity that remains
 *
 * Notes and assumptions:
 * - A handle appearing in into[] may appear later in merge1[] or merge2[].
 * - All arrays have length nmerges.
 * - Memory for these arrays is allocated using the gravity allocator.
 * - The struct must be destroyed with gravity_merge_info_destroy().
 */
struct gravity_merge_info {
  size_t nmerges;
  struct gravity_handle *merge1;
  struct gravity_handle *merge2;
  struct gravity_handle *into;
};

/*
 * Iterator over entities within a rectangular region.
 *
 * This is a stateful, single-pass iterator.
 *
 * The iterator becomes invalid if the gravity object is modified in any way
 * after initialization (including creation, deletion, or updates).
 *
 * Running the iterator when invalid results in undefined behavior.
 */
struct gravity_entity_iter {
  size_t i;   /* internal iteration index */
  double tlx; /* top-left x */
  double tly; /* top-left y */
  double brx; /* bottom-right x */
  double bry; /* bottom-right y */
};

/*
 * Internal slot metadata.
 *
 * Each slot either references a live entity (via entity_idx) or is free.
 * generation is incremented whenever the slot is reused, invalidating
 * previously issued handles.
 */
struct gravity_entity_slot {
  size_t entity_idx;
  size_t generation;
};

/*
 * Core gravity simulation object.
 *
 * This struct owns all simulation state and memory.
 * It must be initialized with gravity_init() before use.
 *
 * Memory layout overview:
 * - Slots map stable handles to densely-packed entity indices.
 * - Entity state is stored in parallel arrays (SoA layout).
 * - free_slots is a stack of reusable slot indices.
 *
 * Internal invariants:
 * - entity_len <= entity_cap
 * - slots_len <= slots_cap
 * - free_slots_len <= free_slots_cap
 * - entity_to_slot[entity_idx] maps back to a slot index
 *
 * Users should treat this struct as opaque outside of implementation code.
 */
struct gravity {
  /* allocator used for all dynamic memory */
  struct allocator_info alloc;

  /* physics parameters */
  double gravitational_constant;
  double softening_factor;
  bool enable_merging;
  double merge_distance_squared;

  /* freelist of unused slots */
  size_t free_slots_len;
  size_t free_slots_cap;
  size_t *free_slots;

  /* slot table for handle indirection */
  size_t slots_len;
  size_t slots_cap;
  struct gravity_entity_slot *slots;

  /* entity data (structure-of-arrays) */
  size_t entity_len;
  size_t entity_cap;
  double *px;
  double *py;
  double *vx;
  double *vy;

  /* intermediate acceleration buffers (double-buffered) */
  double *ax1;
  double *ay1;
  double *ax2;
  double *ay2;

  double *mass;

  /* mapping from entity index to slot index */
  size_t *entity_to_slot;
};

/*
 * Error handling conventions used by functions below:
 *
 * - Functions that may allocate memory return:
 *     * 0 on success
 *     * negative on allocation failure (object may be left partially updated,
 *       but remains safe to destroy)
 *     * positive nonzero on user error (e.g. invalid handle); object remains
 * stable
 *
 * - Functions documented as not allocating memory never fail due to allocation.
 *
 * Unless otherwise specified, functions do not deallocate memory.
 */

/*
 * Deallocate all memory owned by the gravity object.
 *
 * After this call, the object is left in an uninitialized state.
 * It must not be used again unless gravity_init() is called.
 *
 * It is valid to call this on a partially-initialized or partially-failed
 * object (e.g. after allocation failure).
 */
void gravity_destroy(struct gravity *g);

/*
 * Initialize a gravity object with the given allocator.
 *
 * This function performs no dynamic allocation.
 * All internal pointers are set to a state where gravity_destroy() is safe.
 *
 * The allocator provided here will be used for the entire lifetime of the
 * gravity object and for all objects derived from it (e.g. merge info).
 */
void gravity_init(struct gravity *g, struct allocator_info alloc);

/*
 * Reset all simulation state and configure physics parameters.
 *
 * All entities are deleted and all iterators are invalidated.
 * Previously allocated memory is retained and reused where possible.
 *
 * This function does not deallocate memory and does not fail.
 */
void gravity_clear(struct gravity *g, double gravitational_constant,
                   double softening_factor, bool enable_merging,
                   double merge_distance_squared);

/*
 * Create a new entity in the simulation.
 *
 * On success:
 * - The entity is inserted into the simulation.
 * - A valid handle identifying the entity is written to *h.
 *
 * This function may allocate memory.
 *
 * Returns:
 * - 0 on success
 * - negative on allocation failure (object may be partially updated)
 */
int gravity_create(struct gravity *g, struct gravity_entity e,
                   struct gravity_handle *h);

/*
 * Check whether a handle still refers to a live entity.
 *
 * Returns true if the handle is valid, false otherwise.
 *
 * This function does not allocate memory and does not modify state.
 */
bool gravity_is_handle_valid(const struct gravity *g,
                             struct gravity_handle handle);

/*
 * Retrieve the current state of an entity.
 *
 * If the handle is valid, writes the entity data to *e and returns true.
 * If the handle is invalid, returns false and leaves *e unmodified.
 *
 * This function does not allocate memory.
 */
bool gravity_get(const struct gravity *g, struct gravity_handle h,
                 struct gravity_entity *e);

/*
 * Set the position of an entity.
 *
 * If the handle is valid, updates the entity position and returns 0.
 * If the handle is invalid, returns positive nonzero and performs no changes.
 *
 * This function does not allocate memory.
 */
int gravity_set_position(struct gravity *g, struct gravity_handle h, double x,
                         double y);

/*
 * Set the velocity of an entity.
 *
 * If the handle is valid, updates the entity velocity and returns 0.
 * If the handle is invalid, returns positive nonzero and performs no changes.
 *
 * This function does not allocate memory.
 */
int gravity_set_velocity(struct gravity *g, struct gravity_handle h, double x,
                         double y);

/*
 * Set the mass of an entity.
 *
 * If the handle is valid, updates the entity mass and returns 0.
 * If the handle is invalid, returns positive nonzero and performs no changes.
 *
 * This function does not allocate memory.
 */
int gravity_set_mass(struct gravity *g, struct gravity_handle h, double mass);

/*
 * Delete an entity from the simulation.
 *
 * If the handle is valid, the entity is removed and the slot becomes reusable.
 *
 * This function may allocate memory (e.g. growing the free slot list).
 *
 * Returns:
 * - 0 on success
 * - negative on allocation failure (object may be left partially updated)
 * - positive nonzero if the handle is invalid (no changes are made)
 */
int gravity_delete(struct gravity *g, struct gravity_handle h);

/*
 * Initialize an iterator over entities within the given axis-aligned rectangle.
 *
 * The rectangle is defined by its top-left (tlx, tly) and bottom-right (brx,
 * bry) corners. Boundary points are included.
 *
 * This function only initializes the iterator state; it does not depend on
 * the gravity object and performs no allocation.
 *
 * The iterator must later be advanced using gravity_entity_iter_next(), which
 * requires a gravity object.
 */
void gravity_entities_in_rect_iter(double tlx, double tly, double brx,
                                   double bry,
                                   struct gravity_entity_iter *iter);

/*
 * Advance an entity iterator.
 *
 * On success:
 * - Writes the next matching entity handle to *h
 * - Returns true
 *
 * When no more entities match:
 * - Returns false
 *
 * The iterator becomes invalid if the gravity object is modified after
 * initialization (including entity creation, deletion, or update).
 *
 * Calling this function with an invalid iterator results in undefined behavior.
 *
 * This function does not allocate memory.
 */
bool gravity_entity_iter_next(const struct gravity *g,
                              struct gravity_entity_iter *iter,
                              struct gravity_handle *h);

/*
 * Compute the center of mass of all entities in the simulation.
 *
 * Writes the x and y coordinates of the center of mass to *x and *y.
 *
 * If there are no entities or total mass is zero, behaves as if total mass
 * was 1.
 *
 * This function does not allocate memory.
 */
void gravity_center_of_mass(const struct gravity *g, double *x, double *y);

/*
 * Advance the simulation by a single time step.
 *
 * This updates positions and velocities according to gravitational interaction
 * and applies optional entity merging.
 *
 * If merging is enabled, information about merges that occurred during the step
 * is written into *info. Any memory stored in *info must be released using
 * gravity_merge_info_destroy().
 *
 * This function may allocate memory. The info object must always be destoyed,
 * even if allocation fails.
 *
 * Returns:
 * - 0 on success
 * - negative on allocation failure (object may be left partially updated).
 */
int gravity_update(struct gravity *g, double dt,
                   struct gravity_merge_info *info);

/*
 * Deallocate all memory owned by a gravity_merge_info object.
 *
 * The allocator associated with the gravity object is used.
 * After this call, the merge info object is reset to an empty state.
 *
 * This function does not modify the gravity object itself.
 */
void gravity_merge_info_destroy(const struct gravity *g,
                                struct gravity_merge_info *info);

#endif /* GRAVITY_H */
