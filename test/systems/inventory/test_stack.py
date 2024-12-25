from game.systems.inventory.inventory_controller import Stack


def test_init():
    """
    Test that a Stack object can be trivially initialized under proper conditions
    """
    st = Stack(-110, 0)

    assert st.quantity == 0
    assert st.id == -110

    assert st.ref is not None
    assert st.ref.id == -110
