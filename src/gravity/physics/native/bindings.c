#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <stdbool.h>

#include "gravity.h"

static PyObject *helper_make_tuple_of_doubles(double doubles[],
                                              PyObject *objs_helper[],
                                              int count) {
  PyObject *tuple = NULL;
  for (int i = 0; i < count; i++) {
    objs_helper[i] = NULL;
  }

  for (int i = 0; i < count; i++) {
    if ((objs_helper[i] = PyFloat_FromDouble(doubles[i])) == NULL) {
      goto fail;
    }
  }
  if ((tuple = PyTuple_New(count)) == NULL) {
    goto fail;
  }

  for (int i = 0; i < count; i++) {
    PyTuple_SET_ITEM(tuple, i, objs_helper[i]);
  }

  return tuple;

fail:
  for (int i = 0; i < count; i++) {
    Py_XDECREF(objs_helper[i]);
  }
  Py_XDECREF(tuple);
  return NULL;
}

//////////////////////////////////////////////////

typedef struct {
  PyObject_HEAD struct gravity_handle handle;
  Py_hash_t hash;
} SimulatedEntityHandleObject;

static PyTypeObject SimulatedEntityHandleType;

static PyObject *SimulatedEntityHandle_repr(PyObject *obj) {
  SimulatedEntityHandleObject *self = (SimulatedEntityHandleObject *)obj;
  return PyUnicode_FromFormat("<SimulatedEntityHandle slot=%zu gen=%zu>",
                              self->handle.slot_idx, self->handle.generation);
}

static Py_hash_t SimulatedEntityHandle_hash(PyObject *obj) {
  SimulatedEntityHandleObject *self = (SimulatedEntityHandleObject *)obj;
  return self->hash;
}

static PyObject *SimulatedEntityHandle_richcompare(PyObject *obj, PyObject *oth,
                                                   int op) {
  if (op != Py_EQ && op != Py_NE) {
    Py_RETURN_NOTIMPLEMENTED;
  }
  if (Py_TYPE(oth) != &SimulatedEntityHandleType) {
    Py_RETURN_NOTIMPLEMENTED;
  }

  SimulatedEntityHandleObject *self = (SimulatedEntityHandleObject *)obj;
  SimulatedEntityHandleObject *other = (SimulatedEntityHandleObject *)oth;

  bool eq = (self->handle.slot_idx == other->handle.slot_idx) &&
            (self->handle.generation == other->handle.generation);

  if (op == Py_EQ) {
    return PyBool_FromLong(eq);
  } else {
    return PyBool_FromLong(!eq);
  }
}

static PyTypeObject SimulatedEntityHandleType = {
    .ob_base = PyVarObject_HEAD_INIT(NULL, 0)

                   .tp_name = "_core.SimulatedEntityHandle",
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_DISALLOW_INSTANTIATION,
    .tp_basicsize = sizeof(SimulatedEntityHandleObject),
    .tp_itemsize = 0,

    .tp_repr = SimulatedEntityHandle_repr,
    .tp_hash = SimulatedEntityHandle_hash,
    .tp_richcompare = SimulatedEntityHandle_richcompare,
};

static PyObject *
SimulatedEntityHandle_new_internal(struct gravity_handle handle) {
  SimulatedEntityHandleObject *self =
      PyObject_New(SimulatedEntityHandleObject, &SimulatedEntityHandleType);
  if (self == NULL) {
    return NULL;
  }

  Py_hash_t x = (Py_hash_t)handle.slot_idx;
  Py_hash_t y = (Py_hash_t)handle.generation;
  Py_hash_t hash = x ^ (y + 0x9e3779b9 + (x << 6) + (x >> 2));

  if (hash == -1) {
    hash = -2;
  }

  self->handle = handle;
  self->hash = hash;

  return (PyObject *)self;
}

//////////////////////////////////////////////////

typedef struct {
  PyObject_HEAD PyObject *merged;
  PyObject *into;
} MergeInfoObject;

static PyTypeObject MergeInfoType;

static void MergeInfo_dealloc(PyObject *op) {
  MergeInfoObject *self = (MergeInfoObject *)op;
  Py_XDECREF(self->merged);
  Py_XDECREF(self->into);
  Py_TYPE(self)->tp_free(self);
}

static PyObject *MergeInfo_repr(PyObject *obj) {
  MergeInfoObject *self = (MergeInfoObject *)obj;

  PyObject *merged_repr = PyObject_Repr(self->merged);
  if (merged_repr == NULL) {
    return NULL;
  }

  PyObject *into_repr = PyObject_Repr(self->into);
  if (into_repr == NULL) {
    Py_DECREF(merged_repr);
    return NULL;
  }

  PyObject *result = PyUnicode_FromFormat("<MergeInfo merged=%U into=%U>",
                                          merged_repr, into_repr);

  Py_DECREF(merged_repr);
  Py_DECREF(into_repr);

  return result;
}

static PyMemberDef MergeInfo_members[] = {
    {"merged", Py_T_OBJECT_EX, offsetof(MergeInfoObject, merged), Py_READONLY,
     NULL},
    {"into", Py_T_OBJECT_EX, offsetof(MergeInfoObject, into), Py_READONLY,
     NULL},
};

static PyTypeObject MergeInfoType = {
    .ob_base = PyVarObject_HEAD_INIT(NULL, 0)

                   .tp_name = "_core.MergeInfo",
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_DISALLOW_INSTANTIATION,
    .tp_basicsize = sizeof(MergeInfoObject),
    .tp_itemsize = 0,

    .tp_dealloc = MergeInfo_dealloc,
    .tp_repr = MergeInfo_repr,

    .tp_members = MergeInfo_members,
};

// This function STEALS the passed in references.
static PyObject *MergeInfo_new_internal(PyObject *merged_handle_1,
                                        PyObject *merged_handle_2,
                                        PyObject *into_handle) {
  MergeInfoObject *self = PyObject_New(MergeInfoObject, &MergeInfoType);
  if (self == NULL) {
    Py_DECREF(merged_handle_1);
    Py_DECREF(merged_handle_2);
    Py_DECREF(into_handle);
    return NULL;
  }

  self->merged = NULL;
  self->into = NULL;

  PyObject *tuple = PyTuple_New(2);
  if (tuple == NULL) {
    Py_DECREF(self);
    Py_DECREF(merged_handle_1);
    Py_DECREF(merged_handle_2);
    Py_DECREF(into_handle);
    return NULL;
  }

  PyTuple_SET_ITEM(tuple, 0, merged_handle_1);
  PyTuple_SET_ITEM(tuple, 1, merged_handle_2);

  self->merged = tuple;
  self->into = into_handle;

  return (PyObject *)self;
}

//////////////////////////////////////////////////

typedef struct {
  PyObject_HEAD struct gravity gravity;
} NativeSimulationCoreObject;

static void NativeSimulationCore_dealloc(PyObject *op) {
  NativeSimulationCoreObject *self = (NativeSimulationCoreObject *)op;
  gravity_destroy(&self->gravity);
  Py_TYPE(self)->tp_free(self);
}

static PyObject *NativeSimulationCore_new(PyTypeObject *type, PyObject *args,
                                          PyObject *kwds) {
  (void)args;
  (void)kwds;

  NativeSimulationCoreObject *self;
  self = (NativeSimulationCoreObject *)type->tp_alloc(type, 0);
  if (self == NULL) {
    return NULL;
  }

  struct allocator_info alloc = {
      .malloc = PyMem_RawMalloc,
      .realloc = PyMem_RawRealloc,
      .free = PyMem_RawFree,
  };
  gravity_init(&self->gravity, alloc);

  return (PyObject *)self;
}

static int NativeSimulationCore_init(PyObject *obj, PyObject *args,
                                     PyObject *kwargs) {
  NativeSimulationCoreObject *self = (NativeSimulationCoreObject *)obj;

  static char *kwlist[] = {
      "gravitational_constant",
      "softening_factor",
      "enable_merging",
      "merge_distance_squared",
      NULL,
  };
  double gravitational_constant, softening_factor, merge_distance_squared;
  int enable_merging;
  if (!PyArg_ParseTupleAndKeywords(args, kwargs, "ddpd", kwlist,
                                   &gravitational_constant, &softening_factor,
                                   &enable_merging, &merge_distance_squared)) {
    return -1;
  }

  gravity_clear(&self->gravity, gravitational_constant, softening_factor,
                enable_merging, merge_distance_squared);

  return 0;
}

static PyObject *NativeSimulationCore_create(PyObject *obj, PyObject *args) {
  NativeSimulationCoreObject *self = (NativeSimulationCoreObject *)obj;

  struct gravity_entity e;
  if (!PyArg_ParseTuple(args, "ddddd", &e.px, &e.py, &e.vx, &e.vy, &e.mass)) {
    return NULL;
  }

  struct gravity_handle handle;
  if (gravity_create(&self->gravity, e, &handle) < 0) {
    PyErr_NoMemory();
    return NULL;
  }

  return SimulatedEntityHandle_new_internal(handle);
}

static PyObject *NativeSimulationCore_is_handle_valid(PyObject *obj,
                                                      PyObject *args) {
  NativeSimulationCoreObject *self = (NativeSimulationCoreObject *)obj;

  SimulatedEntityHandleObject *handle;
  if (!PyArg_ParseTuple(args, "O!", &SimulatedEntityHandleType, &handle)) {
    return NULL;
  }

  if (gravity_is_handle_valid(&self->gravity, handle->handle)) {
    Py_RETURN_TRUE;
  } else {
    Py_RETURN_FALSE;
  }
}

static PyObject *NativeSimulationCore_get(PyObject *obj, PyObject *args) {
  NativeSimulationCoreObject *self = (NativeSimulationCoreObject *)obj;

  SimulatedEntityHandleObject *handle;
  if (!PyArg_ParseTuple(args, "O!", &SimulatedEntityHandleType, &handle)) {
    return NULL;
  }

  struct gravity_entity e;
  if (!gravity_get(&self->gravity, handle->handle, &e)) {
    Py_RETURN_NONE;
  }

  double doubles[] = {e.px, e.py, e.vx, e.vy, e.mass};
  PyObject *objs[5];
  return helper_make_tuple_of_doubles(doubles, objs, 5);
}

static PyObject *NativeSimulationCore_set_position(PyObject *obj,
                                                   PyObject *args) {
  NativeSimulationCoreObject *self = (NativeSimulationCoreObject *)obj;

  SimulatedEntityHandleObject *handle;
  double x;
  double y;
  if (!PyArg_ParseTuple(args, "O!dd", &SimulatedEntityHandleType, &handle, &x,
                        &y)) {
    return NULL;
  }

  gravity_set_position(&self->gravity, handle->handle, x, y);

  Py_RETURN_NONE;
}

static PyObject *NativeSimulationCore_set_velocity(PyObject *obj,
                                                   PyObject *args) {
  NativeSimulationCoreObject *self = (NativeSimulationCoreObject *)obj;

  SimulatedEntityHandleObject *handle;
  double x;
  double y;
  if (!PyArg_ParseTuple(args, "O!dd", &SimulatedEntityHandleType, &handle, &x,
                        &y)) {
    return NULL;
  }

  gravity_set_velocity(&self->gravity, handle->handle, x, y);

  Py_RETURN_NONE;
}

static PyObject *NativeSimulationCore_set_mass(PyObject *obj, PyObject *args) {
  NativeSimulationCoreObject *self = (NativeSimulationCoreObject *)obj;

  SimulatedEntityHandleObject *handle;
  double mass;
  if (!PyArg_ParseTuple(args, "O!d", &SimulatedEntityHandleType, &handle,
                        &mass)) {
    return NULL;
  }

  gravity_set_mass(&self->gravity, handle->handle, mass);

  Py_RETURN_NONE;
}

static PyObject *NativeSimulationCore_delete(PyObject *obj, PyObject *args) {
  NativeSimulationCoreObject *self = (NativeSimulationCoreObject *)obj;

  SimulatedEntityHandleObject *handle;
  if (!PyArg_ParseTuple(args, "O!", &SimulatedEntityHandleType, &handle)) {
    return NULL;
  }

  if (gravity_delete(&self->gravity, handle->handle) < 0) {
    PyErr_NoMemory();
    return NULL;
  }

  Py_RETURN_NONE;
}

static PyObject *
SimulatedEntityIterator_new_internal(struct gravity_entity_iter, PyObject *);
static PyObject *NativeSimulationCore_entities_in_rect_iter(PyObject *obj,
                                                            PyObject *args) {
  double topleft_x, topleft_y, bottomright_x, bottomright_y;
  if (!PyArg_ParseTuple(args, "dddd", &topleft_x, &topleft_y, &bottomright_x,
                        &bottomright_y)) {
    return NULL;
  }

  struct gravity_entity_iter iter;
  gravity_entities_in_rect_iter(topleft_x, topleft_y, bottomright_x,
                                bottomright_y, &iter);

  return SimulatedEntityIterator_new_internal(iter, obj);
}

static PyObject *NativeSimulationCore_center_of_mass(PyObject *obj,
                                                     PyObject *unused) {
  NativeSimulationCoreObject *self = (NativeSimulationCoreObject *)obj;
  (void)unused;

  double x, y;
  gravity_center_of_mass(&self->gravity, &x, &y);

  double doubles[] = {x, y};
  PyObject *objs[2];
  return helper_make_tuple_of_doubles(doubles, objs, 2);
}

static PyObject *NativeSimulationCore_update(PyObject *obj, PyObject *args) {
  NativeSimulationCoreObject *self = (NativeSimulationCoreObject *)obj;

  double dt;
  if (!PyArg_ParseTuple(args, "d", &dt)) {
    return NULL;
  }

  Py_BEGIN_ALLOW_THREADS;
  gravity_update(&self->gravity, dt);
  Py_END_ALLOW_THREADS;

  Py_RETURN_NONE;
}

static PyObject *NativeSimulationCore_merge_entities(PyObject *obj,
                                                     PyObject *unused) {
  NativeSimulationCoreObject *self = (NativeSimulationCoreObject *)obj;
  (void)unused;

  struct gravity_merge_info info;
  if (gravity_merge_entities(&self->gravity, &info) < 0) {
    gravity_merge_info_destroy(&self->gravity, &info);
    PyErr_NoMemory();
    return NULL;
  }

  PyObject *list = PyList_New(info.nmerges);
  if (list == NULL) {
    goto fail;
  }

  size_t i;
  for (i = 0; i < info.nmerges; i++) {
    struct gravity_handle merge1 = info.merge1[i];
    struct gravity_handle merge2 = info.merge2[i];
    struct gravity_handle into = info.into[i];

    PyObject *merge1_obj = SimulatedEntityHandle_new_internal(merge1);
    if (merge1_obj == NULL) {
      goto fail;
    }
    PyObject *merge2_obj = SimulatedEntityHandle_new_internal(merge2);
    if (merge2_obj == NULL) {
      Py_DECREF(merge1_obj);
      goto fail;
    }
    PyObject *into_obj = SimulatedEntityHandle_new_internal(into);
    if (into_obj == NULL) {
      Py_DECREF(merge1_obj);
      Py_DECREF(merge2_obj);
      goto fail;
    }

    PyObject *merge_info =
        MergeInfo_new_internal(merge1_obj, merge2_obj, into_obj);
    if (merge_info == NULL) {
      Py_DECREF(merge1_obj);
      Py_DECREF(merge2_obj);
      Py_DECREF(into_obj);
      goto fail;
    }

    PyList_SET_ITEM(list, i, merge_info);
  }

  gravity_merge_info_destroy(&self->gravity, &info);
  return list;

fail:
  gravity_merge_info_destroy(&self->gravity, &info);
  Py_DECREF(list);
  return NULL;
}

static PyMethodDef NativeSimulationCore_methods[] = {
    {"create", NativeSimulationCore_create, METH_VARARGS, NULL},
    {"is_handle_valid", NativeSimulationCore_is_handle_valid, METH_VARARGS,
     NULL},
    {"get", NativeSimulationCore_get, METH_VARARGS, NULL},
    {"set_position", NativeSimulationCore_set_position, METH_VARARGS, NULL},
    {"set_velocity", NativeSimulationCore_set_velocity, METH_VARARGS, NULL},
    {"set_mass", NativeSimulationCore_set_mass, METH_VARARGS, NULL},
    {"delete", NativeSimulationCore_delete, METH_VARARGS, NULL},
    {"entities_in_rect_iter", NativeSimulationCore_entities_in_rect_iter,
     METH_VARARGS, NULL},
    {"center_of_mass", NativeSimulationCore_center_of_mass, METH_NOARGS, NULL},
    {"update", NativeSimulationCore_update, METH_VARARGS, NULL},
    {"merge_entities", NativeSimulationCore_merge_entities, METH_NOARGS, NULL},
    {NULL, NULL, 0, NULL},
};

static PyTypeObject NativeSimulationCoreType = {
    .ob_base = PyVarObject_HEAD_INIT(NULL, 0)

                   .tp_name = "_core.NativeSimulationCore",
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_basicsize = sizeof(NativeSimulationCoreObject),
    .tp_itemsize = 0,

    .tp_dealloc = NativeSimulationCore_dealloc,
    .tp_new = NativeSimulationCore_new,
    .tp_init = NativeSimulationCore_init,
    .tp_methods = NativeSimulationCore_methods,
};

//////////////////////////////////////////////////

typedef struct {
  PyObject_HEAD PyObject *core;
  struct gravity_entity_iter iter;
} SimulatedEntityIteratorObject;

static void SimulatedEntityIterator_dealloc(PyObject *obj) {
  SimulatedEntityIteratorObject *self = (SimulatedEntityIteratorObject *)obj;
  Py_XDECREF(self->core);
  Py_TYPE(self)->tp_free(self);
}

static PyObject *SimulatedEntityIterator_iter(PyObject *self) {
  Py_INCREF(self);
  return self;
}

static PyObject *SimulatedEntityIterator_iternext(PyObject *obj) {
  SimulatedEntityIteratorObject *self = (SimulatedEntityIteratorObject *)obj;
  NativeSimulationCoreObject *core_obj =
      (NativeSimulationCoreObject *)self->core;

  struct gravity_handle h;
  if (!gravity_entity_iter_next(&core_obj->gravity, &self->iter, &h)) {
    PyErr_SetNone(PyExc_StopIteration);
    return NULL;
  }

  return SimulatedEntityHandle_new_internal(h);
}

static PyTypeObject SimulatedEntityIteratorType = {
    .ob_base = PyVarObject_HEAD_INIT(NULL, 0)

                   .tp_name = "_core.SimulatedEntityIterator",
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_DISALLOW_INSTANTIATION,
    .tp_basicsize = sizeof(SimulatedEntityIteratorObject),
    .tp_itemsize = 0,

    .tp_dealloc = SimulatedEntityIterator_dealloc,
    .tp_iter = SimulatedEntityIterator_iter,
    .tp_iternext = SimulatedEntityIterator_iternext,
};

static PyObject *
SimulatedEntityIterator_new_internal(struct gravity_entity_iter iter,
                                     PyObject *core_obj) {
  SimulatedEntityIteratorObject *self =
      PyObject_New(SimulatedEntityIteratorObject, &SimulatedEntityIteratorType);
  if (self == NULL) {
    return NULL;
  }
  self->iter = iter;
  Py_INCREF(core_obj);
  self->core = core_obj;
  return (PyObject *)self;
}

//////////////////////////////////////////////////

static int _core_module_exec(PyObject *m) {
  if (PyType_Ready(&SimulatedEntityHandleType) < 0) {
    return -1;
  }
  if (PyType_Ready(&MergeInfoType) < 0) {
    return -1;
  }
  if (PyType_Ready(&SimulatedEntityIteratorType) < 0) {
    return -1;
  }
  if (PyType_Ready(&NativeSimulationCoreType) < 0) {
    return -1;
  }

  if (PyModule_AddObjectRef(m, "SimulatedEntityHandle",
                            (PyObject *)&SimulatedEntityHandleType) < 0) {
    return -1;
  }
  if (PyModule_AddObjectRef(m, "MergeInfo", (PyObject *)&MergeInfoType) < 0) {
    return -1;
  }
  if (PyModule_AddObjectRef(m, "NativeSimulationCore",
                            (PyObject *)&NativeSimulationCoreType) < 0) {
    return -1;
  }

  return 0;
}

static PyModuleDef_Slot _core_module_slots[] = {
    {Py_mod_exec, _core_module_exec},
    {Py_mod_multiple_interpreters, Py_MOD_MULTIPLE_INTERPRETERS_NOT_SUPPORTED},
    {0, NULL},
};

static struct PyModuleDef _core_module = {
    .m_base = PyModuleDef_HEAD_INIT,
    .m_name = "_core",
    .m_size = 0,
    .m_slots = _core_module_slots,
};

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wmissing-prototypes"
PyMODINIT_FUNC PyInit__core(void) {
#pragma GCC diagnostic pop
  return PyModuleDef_Init(&_core_module);
}
