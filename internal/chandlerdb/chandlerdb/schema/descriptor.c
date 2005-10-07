
/*
 * The C descriptor type
 *
 * Copyright (c) 2003-2005 Open Source Applications Foundation
 * License at http://osafoundation.org/Chandler_0.1_license_terms.htm
 */

#include <Python.h>
#include "structmember.h"

#include "c.h"

static void t_descriptor_dealloc(t_descriptor *self);
static int t_descriptor_traverse(t_descriptor *self,
                                 visitproc visit, void *arg);
static int t_descriptor_clear(t_descriptor *self);
static PyObject *t_descriptor_new(PyTypeObject *type,
                                  PyObject *args, PyObject *kwds);
static int t_descriptor_init(t_descriptor *self,
                             PyObject *args, PyObject *kwds);
static PyObject *t_descriptor___get__(t_descriptor *self,
                                      PyObject *obj, PyObject *type);
static int t_descriptor___set__(t_descriptor *self,
                                PyObject *obj, PyObject *value);
static int t_descriptor___delete__(t_descriptor *self, PyObject *args);
static PyObject *t_descriptor_getAttribute(t_descriptor *self, PyObject *kind);
static PyObject *t_descriptor_unregisterAttribute(t_descriptor *self,
                                                  PyObject *kind);
static PyObject *t_descriptor_registerAttribute(t_descriptor *self,
                                                PyObject *args);
static PyObject *t_descriptor_isValueRequired(t_descriptor *self,
                                              PyObject *item);

static PyObject *_getRef_NAME;
static PyObject *getAttributeValue_NAME;
static PyObject *setAttributeValue_NAME;
static PyObject *removeAttributeValue_NAME;


static PyMemberDef t_descriptor_members[] = {
    { "name", T_OBJECT, offsetof(t_descriptor, name), READONLY,
      "attribute name" },
    { "attrs", T_OBJECT, offsetof(t_descriptor, attrs), READONLY,
      "kind/attribute lookup table" },
    { NULL, 0, 0, 0, NULL }
};

static PyMethodDef t_descriptor_methods[] = {
    { "getAttribute", (PyCFunction) t_descriptor_getAttribute, METH_O, "" },
    { "unregisterAttribute", (PyCFunction) t_descriptor_unregisterAttribute,
      METH_O, "" },
    { "registerAttribute", (PyCFunction) t_descriptor_registerAttribute,
      METH_VARARGS, "" },
    { "isValueRequired", (PyCFunction) t_descriptor_isValueRequired,
      METH_O, "" },
    { NULL, NULL, 0, NULL }
};

static PyTypeObject DescriptorType = {
    PyObject_HEAD_INIT(NULL)
    0,                                          /* ob_size */
    "chandlerdb.schema.c.CDescriptor",          /* tp_name */
    sizeof(t_descriptor),                       /* tp_basicsize */
    0,                                          /* tp_itemsize */
    (destructor)t_descriptor_dealloc,           /* tp_dealloc */
    0,                                          /* tp_print */
    0,                                          /* tp_getattr */
    0,                                          /* tp_setattr */
    0,                                          /* tp_compare */
    0,                                          /* tp_repr */
    0,                                          /* tp_as_number */
    0,                                          /* tp_as_sequence */
    0,                                          /* tp_as_mapping */
    0,                                          /* tp_hash  */
    0,                                          /* tp_call */
    0,                                          /* tp_str */
    0,                                          /* tp_getattro */
    0,                                          /* tp_setattro */
    0,                                          /* tp_as_buffer */
    (Py_TPFLAGS_DEFAULT |
     Py_TPFLAGS_BASETYPE |
     Py_TPFLAGS_HAVE_GC),                       /* tp_flags */
    "attribute descriptor",                     /* tp_doc */
    (traverseproc)t_descriptor_traverse,        /* tp_traverse */
    (inquiry)t_descriptor_clear,                /* tp_clear */
    0,                                          /* tp_richcompare */
    0,                                          /* tp_weaklistoffset */
    0,                                          /* tp_iter */
    0,                                          /* tp_iternext */
    t_descriptor_methods,                       /* tp_methods */
    t_descriptor_members,                       /* tp_members */
    0,                                          /* tp_getset */
    0,                                          /* tp_base */
    0,                                          /* tp_dict */
    (descrgetfunc)t_descriptor___get__,         /* tp_descr_get */
    (descrsetfunc)t_descriptor___set__,         /* tp_descr_set */
    0,                                          /* tp_dictoffset */
    (initproc)t_descriptor_init,                /* tp_init */
    0,                                          /* tp_alloc */
    (newfunc)t_descriptor_new,                  /* tp_new */
};


static void t_descriptor_dealloc(t_descriptor *self)
{
    t_descriptor_clear(self);
    self->ob_type->tp_free((PyObject *) self);
}

static int t_descriptor_traverse(t_descriptor *self,
                                 visitproc visit, void *arg)
{
    Py_VISIT(self->name);
    Py_VISIT(self->attrs);

    return 0;
}

static int t_descriptor_clear(t_descriptor *self)
{
    Py_CLEAR(self->name);
    Py_CLEAR(self->attrs);

    return 0;
}


static PyObject *t_descriptor_new(PyTypeObject *type,
                                  PyObject *args, PyObject *kwds)
{
    t_descriptor *self = (t_descriptor *) type->tp_alloc(type, 0);

    if (self)
    {
        self->name = NULL;
        self->attrs = NULL;
    }

    return (PyObject *) self;
}

static int t_descriptor_init(t_descriptor *self,
                             PyObject *args, PyObject *kwds)
{
    PyObject *name;

    if (!PyArg_ParseTuple(args, "O", &name))
        return -1;

    Py_INCREF(name);
    self->name = name;
    self->attrs = PyDict_New();

    return 0;
}

static t_values *get_attrdict(PyObject *obj, int flags)
{
    switch (flags & ATTRDICT) {
      case VALUE:
        return ((t_item *) obj)->values;
      case REF:
        return ((t_item *) obj)->references;
      case REDIRECT:
        return NULL;
      default:
        return NULL;
    }
}

static PyObject *t_descriptor___get__(t_descriptor *self,
                                      PyObject *obj, PyObject *type)
{
    if (obj == NULL || obj == Py_None)
    {
        Py_INCREF(self);
        return (PyObject *) self;
    }
    else if (((t_item *) obj)->status & STALE)
    {
        PyErr_SetObject(PyExc_StaleItemError, obj);
        return NULL;
    }
    else
    {
        PyObject *kind = ((t_item *) obj)->kind;

        if (kind != Py_None)
        {
            PyObject *uuid = ((t_item *) kind)->uuid;
            t_attribute *attr = (t_attribute *)
                PyDict_GetItem(self->attrs, uuid);

            if (attr != NULL)
            {
                int flags = attr->flags;
                t_values *attrDict = get_attrdict(obj, flags);
                PyObject *value = NULL;
                int found = 0;

                if (attrDict)
                {
                    if (!(flags & PROCESS_GET))
                    {
                        value = PyDict_GetItem(attrDict->dict, self->name);
                        if (value != NULL)
                        {
                            Py_INCREF(value);
                            found = 1;
                        }
                        else
                            found = -1;
                    }
                    else if (flags & REF)
                    {
                        if (PyDict_Contains(attrDict->dict, self->name))
                        {
                            value = PyObject_CallMethodObjArgs((PyObject *) attrDict, _getRef_NAME, self->name, Py_None, attr->otherName, NULL);
                            found = 1;
                        }
                        else
                            found = -1;
                    }
                }

                if (found > 0)
                    ((t_item *) obj)->lastAccess = ++_lastAccess;
                else if (found < 0 && flags & NOINHERIT)
                {
                    if (flags & DEFAULT)
                    {
                        value = attr->defaultValue;
                        Py_INCREF(value);
                    }
                    else
                        PyErr_SetObject(PyExc_AttributeError, self->name);
                }                    
                else
                    value = PyObject_CallMethodObjArgs(obj, getAttributeValue_NAME, self->name, attrDict, attr->attrID, NULL);

                return value;
            }
        }

        {
            PyObject *dict = PyObject_GetAttrString(obj, "__dict__");
            PyObject *value = PyDict_GetItem(dict, self->name);

            Py_DECREF(dict);

            if (value == NULL)
                PyErr_SetObject(PyExc_AttributeError, self->name);
            else
                Py_INCREF(value);

            return value;
        }
    }
}

static int t_descriptor___set__(t_descriptor *self,
                                PyObject *obj, PyObject *value)
{
    if (obj == Py_None)
    {
        PyErr_SetObject(PyExc_AttributeError, self->name);
        return -1;
    }
    else if (((t_item *) obj)->status & STALE)
    {
        PyErr_SetObject(PyExc_StaleItemError, obj);
        return -1;
    }
    else if (value == NULL)
        return t_descriptor___delete__(self, obj);
    else
    {
        PyObject *kind = ((t_item *) obj)->kind;

        if (kind != Py_None)
        {
            PyObject *uuid = ((t_item *) kind)->uuid;
            t_attribute *attr = (t_attribute *)
                PyDict_GetItem(self->attrs, uuid);

            if (attr != NULL)
            {
                int flags = attr->flags;
                t_values *attrDict = get_attrdict(obj, flags);

                if (attrDict)
                {
                    PyObject *oldValue =
                        PyDict_GetItem(attrDict->dict, self->name);

                    if (value == oldValue)
                        return 0;

                    if (flags & SINGLE && !(flags & PROCESS_SET) && oldValue)
                    {
			int eq = PyObject_RichCompareBool(value, oldValue,
                                                          Py_EQ);

			if (eq == -1)
                            PyErr_Clear();
                        else if (eq == 1)
                            return 0;
                    }
                }

                value = PyObject_CallMethodObjArgs(obj, setAttributeValue_NAME, self->name, value, attrDict ? (PyObject *) attrDict : Py_None, flags & REF ? attr->otherName : Py_None, Py_True, Py_False, NULL);

                if (!value)
                    return -1;
                    
                Py_DECREF(value);
                return 0;
            }
        }

        {
            PyObject *dict = PyObject_GetAttrString(obj, "__dict__");

            PyDict_SetItem(dict, self->name, value);
            Py_DECREF(dict);

            return 0;
        }
    }
}

static int t_descriptor___delete__(t_descriptor *self, PyObject *obj)
{
    PyObject *kind = ((t_item *) obj)->kind;

    if (kind != Py_None)
    {
        PyObject *uuid = ((t_item *) kind)->uuid;
        t_attribute *attr = (t_attribute *) PyDict_GetItem(self->attrs, uuid);

        if (attr)
        {
            t_values *attrDict = get_attrdict(obj, attr->flags);
            PyObject *value = PyObject_CallMethodObjArgs(obj, removeAttributeValue_NAME, self->name, attrDict ? (PyObject *) attrDict : Py_None, attr->attrID, NULL);

            if (!value)
                return -1;

            Py_DECREF(value);
            return 0;
        }
    }

    {
        PyObject *dict = PyObject_GetAttrString(obj, "__dict__");
        int err = PyDict_DelItem(dict, self->name);

        Py_DECREF(dict);
        if (err == 0)
            return 0;

        PyErr_SetObject(PyExc_AttributeError, self->name);
        return -1;
    }
}

static PyObject *t_descriptor_getAttribute(t_descriptor *self, PyObject *kind)
{
    PyObject *uuid = ((t_item *) kind)->uuid;
    PyObject *attr = PyDict_GetItem(self->attrs, uuid);

    if (attr != NULL)
    {
        Py_INCREF(attr);
        return attr;
    }

    PyErr_SetObject(PyExc_KeyError, uuid);
    return NULL;
}

static PyObject *t_descriptor_unregisterAttribute(t_descriptor *self,
                                                  PyObject *kind)
{
    PyObject *uuid = ((t_item *) kind)->uuid;
    int err = PyDict_DelItem(self->attrs, uuid);

    if (err == 0)
    {
        PyObject *value = PyDict_Size(self->attrs) == 0 ? Py_True : Py_False;

        Py_INCREF(value);
        return value;
    }

    PyErr_SetObject(PyExc_KeyError, uuid);
    return NULL;
}

static PyObject *t_descriptor_registerAttribute(t_descriptor *self,
                                                PyObject *args)
{
    PyObject *kind, *attr;

    if (!PyArg_ParseTuple(args, "OO", &kind, &attr))
        return NULL;

    PyDict_SetItem(self->attrs, ((t_item *) kind)->uuid, attr);
    Py_RETURN_NONE;
}

static PyObject *t_descriptor_isValueRequired(t_descriptor *self,
                                              PyObject *item)
{
    PyObject *kind = ((t_item *) item)->kind;
    PyObject *uuid = ((t_item *) kind)->uuid;
    t_attribute *attr = (t_attribute *) PyDict_GetItem(self->attrs, uuid);

    if (attr)
    {
        int flags = attr->flags;
        t_values *attrDict = get_attrdict(item, flags);

        return PyTuple_Pack(2,
                            attrDict ? (PyObject *) attrDict : Py_None,
                            attrDict && flags & REQUIRED ? Py_True : Py_False);
    }
    else
        return PyTuple_Pack(2, Py_None, Py_False);
}


void _init_descriptor(PyObject *m)
{
    if (PyType_Ready(&DescriptorType) >= 0)
    {
        if (m)
        {
            Py_INCREF(&DescriptorType);
            PyModule_AddObject(m, "CDescriptor", (PyObject *) &DescriptorType);
            CDescriptor = &DescriptorType;

            _getRef_NAME = PyString_FromString("_getRef");
            getAttributeValue_NAME = PyString_FromString("getAttributeValue");
            setAttributeValue_NAME = PyString_FromString("setAttributeValue");
            removeAttributeValue_NAME = PyString_FromString("removeAttributeValue");
        }
    }
}
