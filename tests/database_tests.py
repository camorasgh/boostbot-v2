import asyncio
import os
import unittest

from core.database import (
    setup_database,
    add_user,
    add_boost_key,
    assign_boost_key_to_user,
    get_boost_keys_for_user,
    check_user_has_valid_boost_key,
    remove_boost_from_key,
    transfer_boost_key,
    update_boosts_for_key,
)


class TestDatabase(unittest.TestCase):
    def setUp(self):
        """Set up test database and async loop"""
        self.test_db = "test_database.db"
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # Initialize database
        self.loop.run_until_complete(setup_database(self.test_db))

        # Test data
        self.test_user_id = 12345
        self.test_boost_key = "TEST-KEY-123"
        self.test_boosts = 5

    def tearDown(self):
        """Clean up test database and close loop"""
        self.loop.close()
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_user_operations(self):
        """Test user addition and retrieval"""
        # Test adding user
        success = self.loop.run_until_complete(
            add_user(self.test_user_id, self.test_db)
        )
        self.assertTrue(success)

        # Test adding same user again (should not fail)
        success = self.loop.run_until_complete(
            add_user(self.test_user_id, self.test_db)
        )
        self.assertTrue(success)

    def test_boost_key_operations(self):
        """Test boost key addition and assignment"""
        # Add boost key
        success = self.loop.run_until_complete(
            add_boost_key(self.test_boost_key, self.test_boosts, self.test_db)
        )
        self.assertTrue(success)

        # Add user
        self.loop.run_until_complete(
            add_user(self.test_user_id, self.test_db)
        )

        # Assign key to user
        success = self.loop.run_until_complete(
            assign_boost_key_to_user(self.test_user_id, self.test_boost_key, self.test_db)
        )
        self.assertTrue(success)

        # Get user's keys
        keys = self.loop.run_until_complete(
            get_boost_keys_for_user(self.test_user_id, self.test_db)
        )
        self.assertEqual(len(keys), 1)
        self.assertEqual(keys[0][0], self.test_boost_key)
        self.assertEqual(keys[0][1], self.test_boosts)

    def test_boost_key_transfer(self):
        """Test transferring boost keys between users"""
        # Setup sender and receiver
        sender_id = 111
        receiver_id = 222

        # Add users and boost key
        self.loop.run_until_complete(add_user(sender_id, self.test_db))
        self.loop.run_until_complete(add_user(receiver_id, self.test_db))
        self.loop.run_until_complete(
            add_boost_key(self.test_boost_key, self.test_boosts, self.test_db)
        )

        # Assign key to sender
        self.loop.run_until_complete(
            assign_boost_key_to_user(sender_id, self.test_boost_key, self.test_db)
        )

        # Transfer key
        success = self.loop.run_until_complete(
            transfer_boost_key(sender_id, receiver_id, self.test_boost_key, self.test_db)
        )
        self.assertTrue(success)

        # Verify transfer
        keys = self.loop.run_until_complete(
            get_boost_keys_for_user(receiver_id, self.test_db)
        )
        self.assertEqual(len(keys), 1)
        self.assertEqual(keys[0][0], self.test_boost_key)

    def test_boost_management(self):
        """Test boost addition and removal"""
        # Setup
        self.loop.run_until_complete(
            add_boost_key(self.test_boost_key, self.test_boosts, self.test_db)
        )

        # Test removing boosts
        success = self.loop.run_until_complete(
            remove_boost_from_key(self.test_boost_key, 2, self.test_db)
        )
        self.assertTrue(success)

        # Test adding boosts
        success = self.loop.run_until_complete(
            update_boosts_for_key(self.test_boost_key, 3, self.test_db, "add")
        )
        self.assertTrue(success)

        # Verify final boost count
        self.loop.run_until_complete(add_user(self.test_user_id, self.test_db))
        self.loop.run_until_complete(
            assign_boost_key_to_user(self.test_user_id, self.test_boost_key, self.test_db)
        )
        keys = self.loop.run_until_complete(
            get_boost_keys_for_user(self.test_user_id, self.test_db)
        )
        self.assertEqual(keys[0][1], 6)  # 5 - 2 + 3 = 6

    def test_error_handling(self):
        """Test various error conditions"""
        # Test invalid boost value
        with self.assertRaises(ValueError):
            self.loop.run_until_complete(
                add_boost_key(self.test_boost_key, -1, self.test_db)
            )

        # Test invalid boost key format
        with self.assertRaises(ValueError):
            self.loop.run_until_complete(
                add_boost_key("", 5, self.test_db)
            )

        # Test transfer to non-existent user
        self.loop.run_until_complete(add_user(111, self.test_db))
        self.loop.run_until_complete(
            add_boost_key(self.test_boost_key, self.test_boosts, self.test_db)
        )
        self.loop.run_until_complete(
            assign_boost_key_to_user(111, self.test_boost_key, self.test_db)
        )

        success = self.loop.run_until_complete(
            transfer_boost_key(111, 999, self.test_boost_key, self.test_db)
        )
        self.assertFalse(success)

    def test_check_valid_boost_key(self):
        """Test checking for valid boost keys"""
        # Setup
        self.loop.run_until_complete(add_user(self.test_user_id, self.test_db))
        self.loop.run_until_complete(
            add_boost_key(self.test_boost_key, self.test_boosts, self.test_db)
        )
        self.loop.run_until_complete(
            assign_boost_key_to_user(self.test_user_id, self.test_boost_key, self.test_db)
        )

        # Check valid key
        result = self.loop.run_until_complete(
            check_user_has_valid_boost_key(self.test_user_id, self.test_db)
        )
        self.assertIsNotNone(result)
        self.assertEqual(result[0], self.test_boost_key)
        self.assertEqual(result[1], self.test_boosts)

        # Remove all boosts and check again
        self.loop.run_until_complete(
            remove_boost_from_key(self.test_boost_key, self.test_boosts, self.test_db)
        )
        result = self.loop.run_until_complete(
            check_user_has_valid_boost_key(self.test_user_id, self.test_db)
        )
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()