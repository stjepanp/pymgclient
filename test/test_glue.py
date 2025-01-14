# -*- coding: utf-8 -*-

# Copyright (c) 2016-2019 Memgraph Ltd. [https://memgraph.com]
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from common import start_memgraph, MEMGRAPH_PORT
import mgclient
import pytest


@pytest.fixture(scope="function")
def memgraph_connection():
    memgraph = start_memgraph()
    conn = mgclient.connect(host="127.0.0.1", port=MEMGRAPH_PORT)
    conn.autocommit = True
    yield conn

    memgraph.kill()
    conn.close()


def test_none(memgraph_connection):
    conn = memgraph_connection
    cursor = conn.cursor()
    cursor.execute("RETURN $value", {'value': None})
    assert cursor.fetchall() == [(None, )]


def test_bool(memgraph_connection):
    conn = memgraph_connection
    cursor = conn.cursor()

    cursor.execute("RETURN $value", {'value': True})
    assert cursor.fetchall() == [(True, )]

    cursor.execute("RETURN $value", {'value': False})
    assert cursor.fetchall() == [(False, )]


def test_integer(memgraph_connection):
    conn = memgraph_connection
    cursor = conn.cursor()

    cursor.execute("RETURN $value", {'value': 42})
    assert cursor.fetchall() == [(42, )]

    cursor.execute("RETURN $value", {'value': -1})
    assert cursor.fetchall() == [(-1, )]

    cursor.execute("RETURN $value", {'value': 3289302198})
    assert cursor.fetchall() == [(3289302198, )]

    with pytest.raises(OverflowError):
        cursor.execute("RETURN $value", {'value': 10**100})


def test_float(memgraph_connection):
    conn = memgraph_connection
    cursor = conn.cursor()
    cursor.execute("RETURN $value", {'value': 42.0})
    assert cursor.fetchall() == [(42.0, )]

    cursor.execute("RETURN $value", {'value': 3.1415962})
    assert cursor.fetchall() == [(3.1415962, )]


def test_string(memgraph_connection):
    conn = memgraph_connection
    cursor = conn.cursor()

    cursor.execute("RETURN $value", {'value': 'the best test'})
    assert cursor.fetchall() == [('the best test', )]

    cursor.execute("RETURN '\u010C\u017D\u0160'")
    assert cursor.fetchall() == [("ČŽŠ", )]

    cursor.execute(
        "RETURN $value", {
            'value': b'\x01\x0C\x01\x7D\x01\x60'.decode('utf-16be')})
    assert cursor.fetchall() == [("ČŽŠ", )]


def test_list(memgraph_connection):
    conn = memgraph_connection
    cursor = conn.cursor()

    cursor.execute("RETURN $value",
                   {'value': [1, 2, None, True, False, 'abc', []]})
    assert cursor.fetchall() == [([1, 2, None, True, False, 'abc', []], )]


def test_map(memgraph_connection):
    conn = memgraph_connection
    cursor = conn.cursor()
    cursor.execute(
        "RETURN $value", {
            'value': {
                'x': 1, 'y': 2, 'map': {
                    'key': 'value'}}})
    assert cursor.fetchall() == [({'x': 1, 'y': 2, 'map': {'key': 'value'}}, )]


def test_node(memgraph_connection):
    conn = memgraph_connection
    cursor = conn.cursor()
    cursor.execute(
        "CREATE (n:Label1:Label2 {prop1 : 1, prop2 : 'prop2'}) "
        "RETURN id(n), n")
    rows = cursor.fetchall()
    node_id, _ = rows[0]
    assert rows == [
        (node_id, mgclient.Node(
            node_id, set(
                ['Label1', 'Label2']), {
                'prop1': 1, 'prop2': 'prop2'}))]

    with pytest.raises(ValueError):
        cursor.execute("RETURN $node", {'node': rows[0][1]})


def test_relationship(memgraph_connection):
    conn = memgraph_connection
    cursor = conn.cursor()
    cursor.execute(
        "CREATE (n)-[e:Type {prop1 : 1, prop2 : 'prop2'}]->(m) "
        "RETURN id(n), id(m), id(e), e")
    rows = cursor.fetchall()
    start_id, end_id, edge_id, _ = rows[0]
    assert rows == [(start_id, end_id, edge_id, mgclient.Relationship(
        edge_id, start_id, end_id, "Type", {'prop1': 1, 'prop2': 'prop2'}))]

    with pytest.raises(ValueError):
        cursor.execute("RETURN $rel", {'rel': rows[0][3]})


def test_path(memgraph_connection):
    conn = memgraph_connection
    cursor = conn.cursor()
    cursor.execute(
        "CREATE p = (n1:Node1)<-[e1:Edge1]-(n2:Node2)-[e2:Edge2]->(n3:Node3) "
        "RETURN id(n1), id(n2), id(n3), id(e1), id(e2), p")
    rows = cursor.fetchall()
    n1_id, n2_id, n3_id, e1_id, e2_id, _ = rows[0]
    n1 = mgclient.Node(n1_id, set(["Node1"]), {})
    n2 = mgclient.Node(n2_id, set(["Node2"]), {})
    n3 = mgclient.Node(n3_id, set(["Node3"]), {})
    e1 = mgclient.Relationship(e1_id, n2_id, n1_id, "Edge1", {})
    e2 = mgclient.Relationship(e2_id, n2_id, n3_id, "Edge2", {})

    assert rows == [(n1_id, n2_id, n3_id, e1_id, e2_id,
                     mgclient.Path([n1, n2, n3], [e1, e2]))]

    with pytest.raises(ValueError):
        cursor.execute("RETURN $path", {'path': rows[0][5]})
