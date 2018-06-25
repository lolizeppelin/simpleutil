#include <time.h>
#include <Python.h>
#include "structmember.h"

#define MAXINT 4294967295
//unsigned long MAXINT = ((unsigned long)1 << 32) - 1;

typedef struct {
	PyObject_HEAD
//	PyObject_VAR_HEAD
    unsigned int _size;
    unsigned long _max;
    void *_map_array;
} _bitMapObject;


static void bitmap_dealloc(_bitMapObject *self)
{
    if (self->_size < 64) {
        free((int *)(self->_map_array));
    } else {
        free((long *)(self->_map_array));
    }
    Py_TYPE(self)->tp_free((PyObject *)self);
}


static PyObject *bitmap_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    _bitMapObject *self;
    self = (_bitMapObject *)type->tp_alloc(type, 0);

    return (PyObject *)self;
}



static int bitmap_init(_bitMapObject *self, PyObject *args, PyObject *kwds)
{
    unsigned long max;
    unsigned int size;

    static char *kwlist[] = {"max", NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "k", kwlist, &max)) goto error;

    if (max >= MAXINT) {
        size = 64;
        unsigned long *arrays;
        arrays = (unsigned long *)malloc(sizeof(unsigned long)*(max/size + 1));
        if (arrays == NULL) goto error;
        memset(arrays, 0, sizeof(long)*(max/size + 1));
        self->_map_array = arrays;
    }
    else {
        size = 32;
        unsigned int *arrays;
        arrays = (unsigned int *)malloc(sizeof(unsigned int)*(max/size + 1));
        if (arrays == NULL) goto error;
        memset(arrays, 0, sizeof(int)*(max/size + 1));
        self->_map_array = arrays;
    }
    self->_size = size;
    self->_max = max;

    return 0;

    error:
        PyErr_SetString(PyExc_ValueError, "args value error or malloc oversize");
        return -1;
}


static PyMemberDef bitMapMembers[] = {
	{"size", T_UINT, offsetof(_bitMapObject, _size), READONLY, "Pre size bitmap"},
	{"max", T_ULONG, offsetof(_bitMapObject, _max), READONLY, "Max value of bitmap"},
	{NULL} /* Sentinel */
};

static PyObject *bitmap_add(_bitMapObject *self, PyObject *args)
{
    unsigned long input;
    if (!PyArg_ParseTuple(args, "k", &input)) return NULL;
    if (input > self->_max) {
        PyErr_SetString(PyExc_ValueError, "value over max size");
        return NULL;
    }

    if (self->_size < 64) {
        unsigned int value = (unsigned int)input;
        unsigned int index = value/(self->_size);
        ((int *)self->_map_array)[index] |= (1 << (value % self->_size));
    } else {
        unsigned long value = input;
        unsigned long index = value/self->_size;
        ((long *)self->_map_array)[index] |= (1 << (value % self->_size));
    }

	Py_INCREF(Py_None);
	return Py_None;
}


static PyObject *bitmap_has(_bitMapObject *self, PyObject *args)
{
    unsigned long input;
    unsigned short success = 0;

    if (!PyArg_ParseTuple(args, "k", &input)) return NULL;
    if (input > self->_max) {
        PyErr_SetString(PyExc_ValueError, "value over max size");
        return NULL;
    }

    if (self->_size < 64) {
        unsigned int value = 1 << ((unsigned int)input % self->_size);
        unsigned int index = value/self->_size;
        if ((((unsigned long *)self->_map_array)[index] & value) > 0) success = 1;
    } else {
        unsigned long value = 1 << (input % self->_size);
        unsigned long index = value/self->_size;
        if ((((unsigned long *)self->_map_array)[index] & value) > 0) success = 1;
    }
    return Py_BuildValue("H", success);
}


static PyObject *bitmap_get(_bitMapObject *self, PyObject *args)
{
    unsigned long index;
     PyObject *result;

    if (!PyArg_ParseTuple(args, "k", &index)) return NULL;

    unsigned long max_index = (unsigned long)(self->_max / self->_size) + 1;
    if (index > max_index) {
        PyErr_SetString(PyExc_ValueError, "index over range");
        return NULL;
    }

    if (self->_size < 64) {
        result = Py_BuildValue("I", ((unsigned int *)self->_map_array)[index]);
    } else {
        result = Py_BuildValue("k", ((unsigned long *)self->_map_array)[index]);
    }
     return result;
}


static PyMethodDef bitMapMethods[] = {
    {"add", (PyCFunction)bitmap_add, METH_VARARGS, "Add value into bit map"},
    {"has", (PyCFunction)bitmap_has, METH_VARARGS, "If has value in bit map, return True"},
    {"get", (PyCFunction)bitmap_get, METH_VARARGS, "Get one bitmap from arrays"},
    {NULL, NULL},  /* sentinel */
};



static PyTypeObject _bitMap_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_cutils.bitMap",   /*tp_name*/
    sizeof(_bitMapObject),     /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)bitmap_dealloc,            /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE ,        /*tp_flags*/
    "C bitMap objects",           /*tp_doc*/
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* t* p_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    bitMapMethods,             /* tp_methods */
    bitMapMembers,             /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)bitmap_init,     /* tp_init */
    0,                         /* tp_alloc */
    bitmap_new,                /* tp_new */
};


static PyObject *Cmonotonic(PyObject *self, PyObject *args) {
    struct timespec ts;
    PyObject* millisecond;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    millisecond = Py_BuildValue("k", ts.tv_sec*1000 + ts.tv_nsec / 1000000);
    return millisecond;
}


static PyMethodDef CutilsMethods[] = {
    {"monotonic", (PyCFunction)Cmonotonic, METH_NOARGS, "Get millisecond by CLOCK_MONOTONIC"},
    {NULL, NULL},  /* sentinel */
};


PyMODINIT_FUNC
init_cutils(void){

    PyObject *module;

    if (PyType_Ready(&_bitMap_Type) < 0) goto error;

    module = Py_InitModule3("_cutils", CutilsMethods, "C utils for get monotonic and get a bitmap");
    if (module == NULL) goto error;

    _bitMap_Type.ob_type = &PyType_Type;
    _bitMap_Type.tp_alloc = PyType_GenericAlloc;
    _bitMap_Type.tp_new = PyType_GenericNew;

	Py_INCREF(&_bitMap_Type);
	PyModule_AddObject(module, "bitMap", (PyObject *)&_bitMap_Type);

    error:
        if (PyErr_Occurred()) {
            PyErr_SetString(PyExc_ImportError,
                    "_cutils: init failed");
            module = NULL;
        }
}
