import pygame

from PhySimEngine.Entity import Entity
from PhySimEngine.Scenario import Scenario
from PhySimObjects.SimpleObjects.Movable import Movable
from PhySimObjects.SimpleObjects.Collision import Collision
from PhySimObjects.SimpleObjects.Mass import Mass
from PhySimObjects.SimpleObjects.RecieveForce import ReceiveForce
from PhySimObjects.CircleShape import CircleShape
from PhySimObjects.SimpleObjects.ForceField import ForceField


class ForceFieldCircle(Entity, Movable, Collision, Mass, ReceiveForce):
    """
    A circular entity that is primarily affected by ForceField objects,
    handles screen border collisions, and has basic physics properties.
    It does NOT implement global gravitational attraction or attraction from Attractors.
    """
    def __init__(self, x: int, y: int, radius: float, color: tuple,
                 initial_velocity: pygame.Vector2, mass: float = 1.0,
                 restitution: float = 0.7):
        Entity.__init__(self, x, y)
        Movable.__init__(self, initial_velocity)
        Mass.__init__(self, mass)
        ReceiveForce.__init__(self)

        self.restitution = restitution
        self.shape = CircleShape(radius)
        Collision.__init__(self, self.shape)

        self.color = color
        self.radius = radius

        self.net_force_accumulated = pygame.Vector2(0, 0)
        self.pending_velocity_change = pygame.Vector2(0, 0)
        self.pending_position_correction = pygame.Vector2(0, 0)

    def get_collision_shape(self) -> CircleShape:
        """Returns the circle's shape for collision detection."""
        return self.shape

    def resolve_collision(self, other: 'Collision'):
        """
        Handles collision resolution. For this class, we'll only resolve
        collisions with other ForceFieldCircles for simplicity.
        """
        if isinstance(other, ForceFieldCircle):
            other_circle = other
            distance = self.position.distance_to(other_circle.position)
            combined_radii = self.radius + other_circle.radius

            if distance < combined_radii and distance != 0:
                overlap = combined_radii - distance
                direction = (self.position - other_circle.position).normalize()

                self.pending_position_correction += direction * (overlap / 2)
                other_circle.pending_position_correction -= direction * (overlap / 2)

                relative_velocity = self.velocity - other_circle.velocity
                velocity_along_normal = relative_velocity.dot(direction)

                if velocity_along_normal < 0:
                    e = min(self.restitution, other_circle.restitution)
                    j = -(1 + e) * velocity_along_normal
                    j_divisor = (1 / self.mass) + (1 / other_circle.mass)
                    if j_divisor == 0:
                        return

                    j /= j_divisor

                    impulse = j * direction
                    self.pending_velocity_change += impulse / self.mass
                    other_circle.pending_velocity_change -= impulse / other_circle.mass

    def get_mass(self) -> float:
        return self.mass

    def apply_force(self, force: pygame.Vector2, delta_time: float):
        self.net_force_accumulated += force

    def apply_movement(self, delta_time: float):
        self.position += self.velocity * delta_time

    def calculate_physics(self, delta_time: float, scenario: Scenario):
        for other_entity in scenario.entity_manager.get_entities():
            if isinstance(other_entity, ForceField):
                field_force = other_entity.get_applied_force(self)
                self.apply_force(field_force, delta_time)

        self.pending_velocity_change = pygame.Vector2(0, 0)
        self.pending_position_correction = pygame.Vector2(0, 0)

        for other_entity in scenario.entity_manager.get_entities():
            if other_entity is not self and isinstance(other_entity, Collision):
                if isinstance(other_entity, ForceFieldCircle):
                    if self.get_collision_shape().intersects(other_entity.get_collision_shape(), self.position, other_entity.position):
                        self.resolve_collision(other_entity)

    def update(self, delta_time: float, scenario: Scenario):
        if self.mass > 0:
            acceleration = self.net_force_accumulated / self.mass
            self.velocity += acceleration * delta_time
        self.net_force_accumulated = pygame.Vector2(0, 0)

        self.velocity += self.pending_velocity_change
        self.position += self.pending_position_correction

        self.apply_movement(delta_time)

        screen_rect = scenario.display_surface.get_rect()
        if self.position.x - self.radius < screen_rect.left:
            self.position.x = screen_rect.left + self.radius
            self.velocity.x *= -self.restitution
            if abs(self.velocity.x) < 0.1: self.velocity.x = 0
        if self.position.x + self.radius > screen_rect.right:
            self.position.x = screen_rect.right - self.radius
            self.velocity.x *= -self.restitution
            if abs(self.velocity.x) < 0.1: self.velocity.x = 0
        if self.position.y - self.radius < screen_rect.top:
            self.position.y = screen_rect.top + self.radius
            self.velocity.y *= -self.restitution
            if abs(self.velocity.y) < 0.1: self.velocity.y = 0
        if self.position.y + self.radius > screen_rect.bottom:
            self.position.y = screen_rect.bottom - self.radius
            self.velocity.y *= -self.restitution
            if abs(self.velocity.y) < 0.1: self.velocity.y = 0

    def render(self, surface: pygame.Surface):
        self.shape.render_shape(surface, self.position, self.color)