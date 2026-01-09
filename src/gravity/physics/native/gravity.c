#include "gravity.h"
#include <math.h>
#include <omp.h>

void gravity_destroy(struct gravity *g) {
  g->alloc.free(g->free_slots);

  g->alloc.free(g->slots);

  g->alloc.free(g->px);
  g->alloc.free(g->py);
  g->alloc.free(g->vx);
  g->alloc.free(g->vy);
  g->alloc.free(g->mass);
  g->alloc.free(g->entity_to_slot);
  g->alloc.free(g->ax1);
  g->alloc.free(g->ay1);
  g->alloc.free(g->ax2);
  g->alloc.free(g->ay2);

  // zeroize pointers and capacity
  gravity_init(g, g->alloc);
}

void gravity_init(struct gravity *g, struct allocator_info alloc) {
  g->alloc = alloc;

  g->free_slots_cap = 0;
  g->free_slots = NULL;

  g->slots_cap = 0;
  g->slots = NULL;

  g->entity_cap = 0;
  g->px = NULL;
  g->py = NULL;
  g->vx = NULL;
  g->vy = NULL;
  g->mass = NULL;
  g->entity_to_slot = NULL;
  g->ax1 = NULL;
  g->ay1 = NULL;
  g->ax2 = NULL;
  g->ay2 = NULL;
}

void gravity_clear(struct gravity *g, double gravitational_constant,
                   double softening_factor, bool enable_merging,
                   double merge_distance_squared) {
  g->gravitational_constant = gravitational_constant;
  g->softening_factor = softening_factor;
  g->enable_merging = enable_merging;
  g->merge_distance_squared = merge_distance_squared;

  // truncate arrays (but do not deallocate)
  g->free_slots_len = 0;
  g->slots_len = 0;
  g->entity_len = 0;
}

static inline int grow_free_slots(struct gravity *g) {
  if (g->free_slots_cap == 0) {
    g->free_slots_cap = 64;
    g->free_slots = g->alloc.malloc(sizeof(*g->free_slots) * g->free_slots_cap);
    if (g->free_slots == NULL) {
      return -1;
    }
  }

  size_t new_cap = g->free_slots_cap;
  while (g->free_slots_len + 1 > new_cap) {
    new_cap *= 2;
  }

  if (g->free_slots_cap < new_cap) {
    void *tmp =
        g->alloc.realloc(g->free_slots, sizeof(*g->free_slots) * new_cap);
    if (tmp == NULL) {
      return -1;
    }
    g->free_slots = tmp;
  }

  g->free_slots_len += 1;
  return 0;
}

static inline int grow_slots(struct gravity *g) {
  if (g->slots_cap == 0) {
    g->slots_cap = 64;
    g->slots = g->alloc.malloc(sizeof(*g->slots) * g->slots_cap);
    if (g->slots == NULL) {
      return -1;
    }
  }

  size_t new_cap = g->slots_cap;
  while (g->slots_len + 1 > new_cap) {
    new_cap *= 2;
  }

  if (g->slots_cap < new_cap) {
    void *tmp = g->alloc.realloc(g->slots, sizeof(*g->slots) * new_cap);
    if (tmp == NULL) {
      return -1;
    }
    g->slots = tmp;
  }

  g->slots_len += 1;
  return 0;
}

static inline int grow_entities(struct gravity *g) {
  if (g->entity_cap == 0) {
    g->entity_cap = 64;

    g->px = g->alloc.malloc(sizeof(*g->px) * g->entity_cap);
    if (g->px == NULL) {
      goto initial_malloc_failed;
    }

    g->py = g->alloc.malloc(sizeof(*g->py) * g->entity_cap);
    if (g->py == NULL) {
      goto initial_malloc_failed;
    }

    g->vx = g->alloc.malloc(sizeof(*g->vx) * g->entity_cap);
    if (g->vx == NULL) {
      goto initial_malloc_failed;
    }

    g->vy = g->alloc.malloc(sizeof(*g->vy) * g->entity_cap);
    if (g->vy == NULL) {
      goto initial_malloc_failed;
    }

    g->mass = g->alloc.malloc(sizeof(*g->mass) * g->entity_cap);
    if (g->mass == NULL) {
      goto initial_malloc_failed;
    }

    g->entity_to_slot =
        g->alloc.malloc(sizeof(*g->entity_to_slot) * g->entity_cap);
    if (g->entity_to_slot == NULL) {
      goto initial_malloc_failed;
    }

    g->ax1 = g->alloc.malloc(sizeof(*g->ax1) * g->entity_cap);
    if (g->ax1 == NULL) {
      goto initial_malloc_failed;
    }

    g->ay1 = g->alloc.malloc(sizeof(*g->ay1) * g->entity_cap);
    if (g->ay1 == NULL) {
      goto initial_malloc_failed;
    }

    g->ax2 = g->alloc.malloc(sizeof(*g->ax2) * g->entity_cap);
    if (g->ax2 == NULL) {
      goto initial_malloc_failed;
    }

    g->ay2 = g->alloc.malloc(sizeof(*g->ay2) * g->entity_cap);
    if (g->ay2 == NULL) {
      goto initial_malloc_failed;
    }
  }

  size_t new_cap = g->entity_cap;
  while (g->entity_len + 1 > new_cap) {
    new_cap *= 2;
  }

  void *px = NULL;
  void *py = NULL;
  void *vx = NULL;
  void *vy = NULL;
  void *mass = NULL;
  void *entity_to_slot = NULL;
  void *ax1 = NULL;
  void *ay1 = NULL;
  void *ax2 = NULL;
  void *ay2 = NULL;
  if (g->entity_cap < new_cap) {
    px = g->alloc.realloc(g->px, sizeof(*g->px) * new_cap);
    if (px == NULL) {
      goto realloc_failed;
    }
    py = g->alloc.realloc(g->py, sizeof(*g->py) * new_cap);
    if (py == NULL) {
      goto realloc_failed;
    }
    vx = g->alloc.realloc(g->vx, sizeof(*g->vx) * new_cap);
    if (vx == NULL) {
      goto realloc_failed;
    }
    vy = g->alloc.realloc(g->vy, sizeof(*g->vy) * new_cap);
    if (vy == NULL) {
      goto realloc_failed;
    }
    mass = g->alloc.realloc(g->mass, sizeof(*g->mass) * new_cap);
    if (mass == NULL) {
      goto realloc_failed;
    }
    entity_to_slot = g->alloc.realloc(g->entity_to_slot,
                                      sizeof(*g->entity_to_slot) * new_cap);
    if (entity_to_slot == NULL) {
      goto realloc_failed;
    }
    ax1 = g->alloc.realloc(g->ax1, sizeof(*g->ax1) * new_cap);
    if (ax1 == NULL) {
      goto realloc_failed;
    }
    ay1 = g->alloc.realloc(g->ay1, sizeof(*g->ay1) * new_cap);
    if (ay1 == NULL) {
      goto realloc_failed;
    }
    ax2 = g->alloc.realloc(g->ax2, sizeof(*g->ax2) * new_cap);
    if (ax2 == NULL) {
      goto realloc_failed;
    }
    ay2 = g->alloc.realloc(g->ay2, sizeof(*g->ay2) * new_cap);
    if (ay2 == NULL) {
      goto realloc_failed;
    }

    g->px = px;
    g->py = py;
    g->vx = vx;
    g->vy = vy;
    g->mass = mass;
    g->entity_to_slot = entity_to_slot;
    g->ax1 = ax1;
    g->ay1 = ay1;
    g->ax2 = ax2;
    g->ay2 = ay2;
    g->entity_cap = new_cap;
  }

  g->entity_len += 1;
  return 0;

initial_malloc_failed:
  // init already ensured they start NULL
  g->alloc.free(g->px);
  g->alloc.free(g->py);
  g->alloc.free(g->vx);
  g->alloc.free(g->vy);
  g->alloc.free(g->mass);
  g->alloc.free(g->entity_to_slot);
  g->alloc.free(g->ax1);
  g->alloc.free(g->ay1);
  g->alloc.free(g->ax2);
  g->alloc.free(g->ay2);
  g->entity_cap = 0;
  return -1;

realloc_failed:
  g->alloc.free(px);
  g->alloc.free(py);
  g->alloc.free(vx);
  g->alloc.free(vy);
  g->alloc.free(mass);
  g->alloc.free(entity_to_slot);
  g->alloc.free(ax1);
  g->alloc.free(ay1);
  g->alloc.free(ax2);
  g->alloc.free(ay2);
  return -1;
}

int gravity_create(struct gravity *g, struct gravity_entity e,
                   struct gravity_handle *h) {
  struct gravity_entity_slot *slot;
  size_t slot_idx;
  if (g->free_slots_len == 0) {
    slot_idx = g->slots_len;
    if (grow_slots(g) < 0) {
      return -1;
    }
    slot = &g->slots[slot_idx];
    slot->generation = 0;
  } else {
    g->free_slots_len -= 1;
    slot_idx = g->free_slots[g->free_slots_len];
    slot = &g->slots[slot_idx];
  }

  size_t entity_idx = g->entity_len;
  if (grow_entities(g) < 0) {
    return -1;
  }

  g->px[entity_idx] = e.px;
  g->py[entity_idx] = e.py;
  g->vx[entity_idx] = e.vx;
  g->vy[entity_idx] = e.vy;
  g->mass[entity_idx] = e.mass;
  g->entity_to_slot[entity_idx] = slot_idx;

  slot->entity_idx = entity_idx;
  h->slot_idx = slot_idx;
  h->generation = slot->generation;

  return 0;
}

bool gravity_is_handle_valid(const struct gravity *g, struct gravity_handle h) {
  return h.slot_idx < g->slots_len &&
         g->slots[h.slot_idx].generation == h.generation;
}

bool gravity_get(const struct gravity *g, struct gravity_handle h,
                 struct gravity_entity *e) {
  if (!gravity_is_handle_valid(g, h)) {
    return false;
  }

  size_t entity_idx = g->slots[h.slot_idx].entity_idx;
  e->px = g->px[entity_idx];
  e->py = g->py[entity_idx];
  e->vx = g->vx[entity_idx];
  e->vy = g->vy[entity_idx];
  e->mass = g->mass[entity_idx];
  return true;
}

int gravity_set_position(struct gravity *g, struct gravity_handle h, double x,
                         double y) {
  if (!gravity_is_handle_valid(g, h)) {
    return 1;
  }

  size_t entity_idx = g->slots[h.slot_idx].entity_idx;
  g->px[entity_idx] = x;
  g->py[entity_idx] = y;
  return 0;
}
int gravity_set_velocity(struct gravity *g, struct gravity_handle h, double x,
                         double y) {
  if (!gravity_is_handle_valid(g, h)) {
    return 1;
  }

  size_t entity_idx = g->slots[h.slot_idx].entity_idx;
  g->vx[entity_idx] = x;
  g->vy[entity_idx] = y;
  return 0;
}

int gravity_set_mass(struct gravity *g, struct gravity_handle h, double mass) {
  if (!gravity_is_handle_valid(g, h)) {
    return 1;
  }

  size_t entity_idx = g->slots[h.slot_idx].entity_idx;
  g->mass[entity_idx] = mass;
  return 0;
}

static int delete_entity(struct gravity *g, size_t entity_idx) {
  size_t slot_idx = g->entity_to_slot[entity_idx];
  size_t last = g->entity_len - 1;

  if (entity_idx != last) {
    g->px[entity_idx] = g->px[last];
    g->py[entity_idx] = g->py[last];
    g->vx[entity_idx] = g->vx[last];
    g->vy[entity_idx] = g->vy[last];
    g->mass[entity_idx] = g->mass[last];

    size_t moved_slot = g->entity_to_slot[last];
    g->entity_to_slot[entity_idx] = moved_slot;
    g->slots[moved_slot].entity_idx = entity_idx;
  }

  g->entity_len -= 1;

  g->slots[slot_idx].generation += 1;
  if (grow_free_slots(g) < 0) {
    return -1;
  }
  g->free_slots[g->free_slots_len - 1] = slot_idx;
  return 0;
}

int gravity_delete(struct gravity *g, struct gravity_handle h) {
  if (!gravity_is_handle_valid(g, h)) {
    return 1;
  }

  size_t entity_idx = g->slots[h.slot_idx].entity_idx;
  return delete_entity(g, entity_idx);
}

void gravity_entities_in_rect_iter(double tlx, double tly, double brx,
                                   double bry,
                                   struct gravity_entity_iter *iter) {
  iter->i = 0;
  iter->tlx = tlx;
  iter->tly = tly;
  iter->brx = brx;
  iter->bry = bry;
}

static void make_handle(const struct gravity *g, struct gravity_handle *h,
                        size_t entity_idx) {
  size_t slot_idx = g->entity_to_slot[entity_idx];
  h->slot_idx = slot_idx;
  h->generation = g->slots[slot_idx].generation;
}

bool gravity_entity_iter_next(const struct gravity *g,
                              struct gravity_entity_iter *iter,
                              struct gravity_handle *h) {
  if (iter->i >= g->entity_len) {
    return false;
  }

  for (size_t i = iter->i; i < g->entity_len; i++) {
    double x = g->px[i];
    double y = g->py[i];
    if (iter->tlx <= x && x <= iter->brx && iter->tly <= y && y <= iter->bry) {
      iter->i = i + 1;
      make_handle(g, h, i);
      return true;
    }
  }

  iter->i = g->entity_len;
  return false;
}

void gravity_center_of_mass(const struct gravity *g, double *x, double *y) {
  double total_mass = 0;
  double cx = 0;
  double cy = 0;

  for (size_t i = 0; i < g->entity_len; i++) {
    double mass = g->mass[i];
    cx += g->px[i] * mass;
    cy += g->py[i] * mass;
    total_mass += mass;
  }

  if (total_mass == 0) {
    total_mass = 1;
  }
  cx /= total_mass;
  cy /= total_mass;

  *x = cx;
  *y = cy;
}

void gravity_merge_info_destroy(const struct gravity *g,
                                struct gravity_merge_info *info) {
  g->alloc.free(info->merge1);
  g->alloc.free(info->merge2);
  g->alloc.free(info->into);
}

static int do_merge_masses(struct gravity *g, size_t i, size_t j,
                           struct gravity_handle *m1, struct gravity_handle *m2,
                           struct gravity_handle *in) {
  double pxi = g->px[i];
  double pyi = g->py[i];
  double vxi = g->vx[i];
  double vyi = g->vy[i];
  double mi = g->mass[i];
  double pxj = g->px[j];
  double pyj = g->py[j];
  double vxj = g->vx[j];
  double vyj = g->vy[j];
  double mj = g->mass[j];

  struct gravity_entity e;
  e.mass = mi + mj;
  e.px = (mi * pxi + mj * pxj) / e.mass;
  e.py = (mi * pyi + mj * pyj) / e.mass;
  e.vx = (mi * vxi + mj * vxj) / e.mass;
  e.vy = (mi * vyi + mj * vyj) / e.mass;

  make_handle(g, m1, i);
  make_handle(g, m2, j);

  if (i < j) {
    size_t tmp = i;
    i = j;
    j = tmp;
  }
  delete_entity(g, i);
  delete_entity(g, j);

  if (gravity_create(g, e, in) < 0) {
    return -1;
  }
  return 0;
}

static int merge_masses(struct gravity *g, struct gravity_handle *m1,
                        struct gravity_handle *m2, struct gravity_handle *in,
                        bool *did_merge) {
  for (size_t i = 0; i < g->entity_len; i++) {
    for (size_t j = i + 1; j < g->entity_len; j++) {
      double rx = g->px[j] - g->px[i];
      double ry = g->py[j] - g->py[i];
      double length = rx * rx + ry * ry;
      if (length <= g->merge_distance_squared) {
        if (do_merge_masses(g, i, j, m1, m2, in) < 0) {
          return -1;
        }
        *did_merge = true;
        return 0;
      }
    }
  }
  *did_merge = false;
  return 0;
}

int gravity_merge_entities(struct gravity *g, struct gravity_merge_info *info) {
  info->nmerges = 0;
  info->merge1 = NULL;
  info->merge2 = NULL;
  info->into = NULL;

  if (!g->enable_merging) {
    return 0;
  }

  size_t len = 0;
  size_t capacity = 0;
  while (true) {
    struct gravity_handle m1, m2, in;
    bool did_merge;
    if (merge_masses(g, &m1, &m2, &in, &did_merge) < 0) {
      return -1;
    }
    if (!did_merge) {
      break;
    }

    if (capacity == 0) {
      capacity = 16;

      info->merge1 = g->alloc.malloc(sizeof(*info->merge1) * capacity);
      if (info->merge1 == NULL) {
        return -1;
      }
      info->merge2 = g->alloc.malloc(sizeof(*info->merge2) * capacity);
      if (info->merge2 == NULL) {
        g->alloc.free(info->merge1);
        return -1;
      }
      info->into = g->alloc.malloc(sizeof(*info->into) * capacity);
      if (info->into == NULL) {
        g->alloc.free(info->merge1);
        g->alloc.free(info->merge2);
        return -1;
      }
    }

    if (capacity <= len) {
      capacity *= 2;

      void *tmp =
          g->alloc.realloc(info->merge1, sizeof(*info->merge1) * capacity);
      if (tmp == NULL) {
        return -1;
      }
      info->merge1 = tmp;

      tmp = g->alloc.realloc(info->merge2, sizeof(*info->merge2) * capacity);
      if (tmp == NULL) {
        return -1;
      }
      info->merge2 = tmp;

      tmp = g->alloc.realloc(info->into, sizeof(*info->into) * capacity);
      if (tmp == NULL) {
        return -1;
      }
      info->into = tmp;
    }

    info->merge1[len] = m1;
    info->merge2[len] = m2;
    info->into[len] = in;
    len += 1;
  }

  info->nmerges = len;
  return 0;
}

static void compute_accelerations(const struct gravity *g,
                                  double *ax,
                                  double *ay) {
  const size_t n = g->entity_len;
  const double G = g->gravitational_constant;
  const double eps = g->softening_factor;

#pragma omp parallel for schedule(static)
  for (size_t i = 0; i < n; i++) {

    double axi = 0.0;
    double ayi = 0.0;

    const double xi = g->px[i];
    const double yi = g->py[i];
    const double mi = g->mass[i];

    for (size_t j = 0; j < n; j++) {
      if (j == i) continue;

      double rx = g->px[j] - xi;
      double ry = g->py[j] - yi;

      double dist_sq = rx * rx + ry * ry + eps;
      double inv_dist = 1.0 / sqrt(dist_sq);
      double inv_dist3 = inv_dist / dist_sq;

      double factor = G * g->mass[j] * inv_dist3;

      axi += rx * factor;
      ayi += ry * factor;
    }

    ax[i] = axi;
    ay[i] = ayi;
  }
}


void gravity_update(struct gravity *g, double dt) {
    const size_t n = g->entity_len;

    compute_accelerations(g, g->ax1, g->ay1);

    #pragma omp parallel for schedule(static)
    for (size_t i = 0; i < n; i++) {
        g->px[i] += g->vx[i] * dt + 0.5 * g->ax1[i] * dt * dt;
        g->py[i] += g->vy[i] * dt + 0.5 * g->ay1[i] * dt * dt;
    }

    compute_accelerations(g, g->ax2, g->ay2);

    #pragma omp parallel for schedule(static)
    for (size_t i = 0; i < n; i++) {
        g->vx[i] += 0.5 * (g->ax1[i] + g->ax2[i]) * dt;
        g->vy[i] += 0.5 * (g->ay1[i] + g->ay2[i]) * dt;
    }
}
