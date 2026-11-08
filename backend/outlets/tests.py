from django.db import IntegrityError, transaction
from django.test import TestCase

from outlets.models import MapEdge, MapNode, Shop
from accounts.models import User
from rest_framework.test import APIClient


class OutletSchemaTests(TestCase):
    def test_coordinate_and_rating_constraints(self):
        for data in [{"latitude": 91, "longitude": 0}, {"latitude": 0, "longitude": 181}, {"latitude": 0, "longitude": 0, "rating": 5.1}]:
            with self.subTest(data=data), self.assertRaises(IntegrityError), transaction.atomic():
                Shop.objects.create(name="Outlet", address="Address", phone="01-0000000", **data)

    def test_edges_require_distinct_unique_nodes_and_cascade(self):
        first = MapNode.objects.create(name="First", latitude=27.7, longitude=85.3)
        second = MapNode.objects.create(name="Second", latitude=27.8, longitude=85.4)
        MapEdge.objects.create(from_node=first, to_node=second)
        with self.assertRaises(IntegrityError), transaction.atomic():
            MapEdge.objects.create(from_node=second, to_node=first)
        with self.assertRaises(IntegrityError), transaction.atomic():
            MapEdge.objects.create(from_node=first, to_node=second)
        with self.assertRaises(IntegrityError), transaction.atomic():
            MapEdge.objects.create(from_node=first, to_node=first)
        first.delete()
        self.assertFalse(MapEdge.objects.exists())


class OutletApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user(username='staff', email='staff@example.com', password='test-password', is_staff=True)
        self.first = MapNode.objects.create(name='First', latitude=27.7, longitude=85.3)
        self.second = MapNode.objects.create(name='Second', latitude=27.8, longitude=85.4)

    def test_public_search_and_graph(self):
        Shop.objects.create(name='Active', address='Kathmandu', phone='123', latitude=27.7, longitude=85.3, rating=0)
        Shop.objects.create(name='Hidden', address='Kathmandu', phone='123', latitude=27.7, longitude=85.3, is_active=False)
        MapEdge.objects.create(from_node=self.first, to_node=self.second)
        response = self.client.get('/api/outlets/', {'search': 'KATH'})
        self.assertEqual([shop['name'] for shop in response.data], ['Active'])
        self.assertEqual(response.data[0]['rating'], '0.0')
        self.assertEqual(self.client.get('/api/outlets/', {'search': 'x' * 101}).status_code, 400)
        graph = self.client.get('/api/outlets/graph/').data
        self.assertEqual((len(graph['nodes']), len(graph['edges'])), (2, 1))

    def test_staff_access_and_validation(self):
        payload = {'from_node': self.first.pk, 'to_node': self.second.pk}
        self.assertIn(self.client.post('/api/admin/map-edges/', payload, format='json').status_code, (401, 403))
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.post('/api/admin/map-edges/', payload, format='json').status_code, 201)
        self.assertEqual(self.client.post('/api/admin/map-edges/', {'from_node': self.second.pk, 'to_node': self.first.pk}, format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/admin/map-edges/', {'from_node': self.first.pk, 'to_node': self.first.pk}, format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/admin/outlets/', {'name': 'Bad', 'address': 'Here', 'phone': '123', 'latitude': 91, 'longitude': 0}, format='json').status_code, 400)
