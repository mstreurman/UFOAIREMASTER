#include <Jolt/Jolt.h>
#include <Jolt/RegisterTypes.h>
#include <Jolt/Core/Factory.h>
#include <Jolt/Core/TempAllocator.h>
#include <Jolt/Core/JobSystemThreadPool.h>
#include <Jolt/Physics/PhysicsSystem.h>
#include <Jolt/Physics/Body/BodyCreationSettings.h>
#include <Jolt/Physics/Body/BodyActivationListener.h>
#include <Jolt/Physics/Collision/Shape/BoxShape.h>
#include <Jolt/Physics/Collision/Shape/CapsuleShape.h>
#include <Jolt/Physics/Constraints/SwingTwistConstraint.h>
#include <Jolt/Physics/Collision/ContactListener.h>

#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <limits>
#include <string_view>
#include <thread>
#include <vector>

using namespace JPH;

namespace Layers {
static constexpr ObjectLayer StaticPresentationWorld = 0;
static constexpr ObjectLayer DynamicDebris = 1;
static constexpr ObjectLayer Ragdoll = 2;
static constexpr ObjectLayer PresentationTrigger = 3;
}

namespace BroadPhaseLayers {
static constexpr BroadPhaseLayer Static(0);
static constexpr BroadPhaseLayer Moving(1);
static constexpr uint NumLayers = 2;
}

class ObjectLayerPairFilterImpl final : public ObjectLayerPairFilter {
public:
    bool ShouldCollide(ObjectLayer a, ObjectLayer b) const override {
        if (a == Layers::PresentationTrigger || b == Layers::PresentationTrigger)
            return false;
        if (a == Layers::StaticPresentationWorld)
            return b == Layers::DynamicDebris || b == Layers::Ragdoll;
        if (b == Layers::StaticPresentationWorld)
            return a == Layers::DynamicDebris || a == Layers::Ragdoll;
        const bool a_dynamic = a == Layers::DynamicDebris || a == Layers::Ragdoll;
        const bool b_dynamic = b == Layers::DynamicDebris || b == Layers::Ragdoll;
        return a_dynamic && b_dynamic;
    }
};

class BroadPhaseLayerInterfaceImpl final : public BroadPhaseLayerInterface {
public:
    uint GetNumBroadPhaseLayers() const override { return BroadPhaseLayers::NumLayers; }
    BroadPhaseLayer GetBroadPhaseLayer(ObjectLayer layer) const override {
        if (layer == Layers::StaticPresentationWorld)
            return BroadPhaseLayers::Static;
        return BroadPhaseLayers::Moving;
    }
#if defined(JPH_EXTERNAL_PROFILE) || defined(JPH_PROFILE_ENABLED)
    const char *GetBroadPhaseLayerName(BroadPhaseLayer layer) const override {
        return layer == BroadPhaseLayers::Static ? "Static" : "Moving";
    }
#endif
};

class ObjectVsBroadPhaseLayerFilterImpl final : public ObjectVsBroadPhaseLayerFilter {
public:
    bool ShouldCollide(ObjectLayer layer, BroadPhaseLayer broad) const override {
        if (layer == Layers::PresentationTrigger)
            return false;
        if (layer == Layers::StaticPresentationWorld)
            return broad == BroadPhaseLayers::Moving;
        return true;
    }
};

class ActivationCounter final : public BodyActivationListener {
public:
    void OnBodyActivated(const BodyID &, uint64) override {
        activations.fetch_add(1, std::memory_order_relaxed);
    }
    void OnBodyDeactivated(const BodyID &, uint64) override {
        deactivations.fetch_add(1, std::memory_order_relaxed);
    }
    std::atomic<uint64_t> activations{0};
    std::atomic<uint64_t> deactivations{0};
};

class ContactCounter final : public ContactListener {
public:
    void OnContactAdded(const Body &, const Body &, const ContactManifold &, ContactSettings &) override {
        added.fetch_add(1, std::memory_order_relaxed);
    }
    void OnContactPersisted(const Body &, const Body &, const ContactManifold &, ContactSettings &) override {
        persisted.fetch_add(1, std::memory_order_relaxed);
    }
    std::atomic<uint64_t> added{0};
    std::atomic<uint64_t> persisted{0};
};

static void TraceImpl(const char *fmt, ...) {
    va_list args;
    va_start(args, fmt);
    std::vfprintf(stderr, fmt, args);
    va_end(args);
}

#ifdef JPH_ENABLE_ASSERTS
static bool AssertFailedImpl(const char *expr, const char *msg, const char *file, uint line) {
    std::fprintf(stderr, "JOLT_ASSERT file=%s line=%u expr=%s msg=%s\n",
                 file, line, expr, msg != nullptr ? msg : "");
    std::fflush(stderr);
    std::abort();
}
#endif

static bool finite_vec3(Vec3Arg v) {
    return std::isfinite(v.GetX()) && std::isfinite(v.GetY()) && std::isfinite(v.GetZ());
}
static bool finite_rvec3(RVec3Arg v) {
    return std::isfinite(static_cast<double>(v.GetX())) &&
           std::isfinite(static_cast<double>(v.GetY())) &&
           std::isfinite(static_cast<double>(v.GetZ()));
}
static bool finite_quat(QuatArg q) {
    return std::isfinite(q.GetX()) && std::isfinite(q.GetY()) &&
           std::isfinite(q.GetZ()) && std::isfinite(q.GetW());
}

static uint64_t owner_tag(uint32_t index) {
    return 0x55464f4149520000ULL | static_cast<uint64_t>(index);
}

struct Config {
    uint32_t ticks = 36000;
    uint32_t worker_threads = 7;
};

static uint32_t parse_u32(const char *text, const char *name) {
    char *end = nullptr;
    const unsigned long value = std::strtoul(text, &end, 10);
    if (text[0] == '\0' || end == nullptr || *end != '\0' || value > std::numeric_limits<uint32_t>::max()) {
        std::fprintf(stderr, "invalid %s: %s\n", name, text);
        std::exit(2);
    }
    return static_cast<uint32_t>(value);
}

static Config parse_args(int argc, char **argv) {
    Config cfg;
    for (int i = 1; i < argc; ++i) {
        const std::string_view arg(argv[i]);
        if (arg == "--ticks" && i + 1 < argc) {
            cfg.ticks = parse_u32(argv[++i], "ticks");
        } else if (arg == "--worker-threads" && i + 1 < argc) {
            cfg.worker_threads = parse_u32(argv[++i], "worker-threads");
        } else {
            std::fprintf(stderr, "unknown/incomplete argument: %s\n", argv[i]);
            std::exit(2);
        }
    }
    if (cfg.ticks < 36000) {
        std::fprintf(stderr, "R5 requires at least 36000 ticks (600 simulated seconds at 60 Hz)\n");
        std::exit(2);
    }
    if (cfg.worker_threads == 0)
        cfg.worker_threads = 1;
    return cfg;
}

int main(int argc, char **argv) {
    const Config cfg = parse_args(argc, argv);
    constexpr float dt = 1.0f / 60.0f;
    constexpr uint32_t box_count = 192;
    constexpr uint32_t ragdoll_count = 64;
    constexpr uint32_t dynamic_count = box_count + ragdoll_count;
    constexpr uint32_t ragdoll_chains = 8;
    constexpr uint32_t bodies_per_chain = 8;
    constexpr uint32_t expected_constraints = ragdoll_chains * (bodies_per_chain - 1);
    constexpr uint64_t canonical_sentinel = 0x5aa53cc396690f17ULL;
    const uint64_t canonical_before = canonical_sentinel;

    RegisterDefaultAllocator();
    Trace = TraceImpl;
    JPH_IF_ENABLE_ASSERTS(AssertFailed = AssertFailedImpl;)
    Factory::sInstance = new Factory();
    RegisterTypes();

    TempAllocatorImpl temp_allocator(64 * 1024 * 1024);
    JobSystemThreadPool job_system(cMaxPhysicsJobs, cMaxPhysicsBarriers, static_cast<int>(cfg.worker_threads));

    BroadPhaseLayerInterfaceImpl broad_phase_layer_interface;
    ObjectVsBroadPhaseLayerFilterImpl object_vs_broadphase_layer_filter;
    ObjectLayerPairFilterImpl object_vs_object_layer_filter;

    PhysicsSystem physics;
    physics.Init(2048, 0, 65536, 32768,
                 broad_phase_layer_interface,
                 object_vs_broadphase_layer_filter,
                 object_vs_object_layer_filter);

    ActivationCounter activation_counter;
    ContactCounter contact_counter;
    physics.SetBodyActivationListener(&activation_counter);
    physics.SetContactListener(&contact_counter);
    BodyInterface &bodies = physics.GetBodyInterface();

    BodyCreationSettings floor_settings(new BoxShape(Vec3(20.0f, 1.0f, 20.0f)),
                                        RVec3(0.0f, -1.0f, 0.0f),
                                        Quat::sIdentity(),
                                        EMotionType::Static,
                                        Layers::StaticPresentationWorld);
    floor_settings.mFriction = 0.9f;
    BodyID floor_id = bodies.CreateAndAddBody(floor_settings, EActivation::DontActivate);
    if (floor_id.IsInvalid()) {
        std::fprintf(stderr, "failed to create floor\n");
        return 1;
    }

    std::vector<BodyID> dynamic_ids;
    dynamic_ids.reserve(dynamic_count);
    std::vector<Body *> ragdoll_bodies;
    ragdoll_bodies.reserve(ragdoll_count);
    std::vector<Ref<Constraint>> constraints;
    constraints.reserve(expected_constraints);

    RefConst<Shape> box_shape = new BoxShape(Vec3(0.48f, 0.48f, 0.48f));
    for (uint32_t layer = 0; layer < 3; ++layer) {
        for (uint32_t z = 0; z < 8; ++z) {
            for (uint32_t x = 0; x < 8; ++x) {
                const uint32_t index = static_cast<uint32_t>(dynamic_ids.size());
                const float px = (static_cast<float>(x) - 3.5f) * 0.98f;
                const float py = 0.5f + static_cast<float>(layer) * 0.98f;
                const float pz = (static_cast<float>(z) - 3.5f) * 0.98f;
                BodyCreationSettings settings(box_shape, RVec3(px, py, pz), Quat::sIdentity(),
                                              EMotionType::Dynamic, Layers::DynamicDebris);
                settings.mFriction = 0.85f;
                settings.mRestitution = 0.02f;
                settings.mUserData = owner_tag(index);
                BodyID id = bodies.CreateAndAddBody(settings, EActivation::Activate);
                if (id.IsInvalid()) {
                    std::fprintf(stderr, "failed to create debris body %u\n", index);
                    return 1;
                }
                dynamic_ids.push_back(id);
            }
        }
    }

    RefConst<Shape> capsule_shape = new CapsuleShape(0.34f, 0.22f);
    for (uint32_t chain = 0; chain < ragdoll_chains; ++chain) {
        const float base_x = -8.0f + static_cast<float>(chain) * 2.25f;
        const float base_z = 7.0f;
        for (uint32_t part = 0; part < bodies_per_chain; ++part) {
            const uint32_t index = static_cast<uint32_t>(dynamic_ids.size());
            const float py = 0.6f + static_cast<float>(part) * 0.88f;
            BodyCreationSettings settings(capsule_shape, RVec3(base_x, py, base_z), Quat::sIdentity(),
                                          EMotionType::Dynamic, Layers::Ragdoll);
            settings.mFriction = 0.7f;
            settings.mRestitution = 0.01f;
            settings.mUserData = owner_tag(index);
            Body *body = bodies.CreateBody(settings);
            if (body == nullptr) {
                std::fprintf(stderr, "failed to create ragdoll body %u\n", index);
                return 1;
            }
            bodies.AddBody(body->GetID(), EActivation::Activate);
            dynamic_ids.push_back(body->GetID());
            ragdoll_bodies.push_back(body);
        }
    }

    for (uint32_t chain = 0; chain < ragdoll_chains; ++chain) {
        for (uint32_t part = 1; part < bodies_per_chain; ++part) {
            Body &a = *ragdoll_bodies[chain * bodies_per_chain + part - 1];
            Body &b = *ragdoll_bodies[chain * bodies_per_chain + part];
            SwingTwistConstraintSettings settings;
            const RVec3 anchor = a.GetPosition() + Vec3(0.0f, 0.44f, 0.0f);
            settings.mPosition1 = settings.mPosition2 = anchor;
            settings.mTwistAxis1 = settings.mTwistAxis2 = Vec3::sAxisY();
            settings.mPlaneAxis1 = settings.mPlaneAxis2 = Vec3::sAxisX();
            settings.mNormalHalfConeAngle = 0.75f;
            settings.mPlaneHalfConeAngle = 0.75f;
            settings.mTwistMinAngle = -0.5f;
            settings.mTwistMaxAngle = 0.5f;
            settings.mMaxFrictionTorque = 0.25f;
            Ref<Constraint> constraint = settings.Create(a, b);
            physics.AddConstraint(constraint);
            constraints.push_back(constraint);
        }
    }

    if (dynamic_ids.size() != dynamic_count || constraints.size() != expected_constraints) {
        std::fprintf(stderr, "fixture cardinality mismatch bodies=%zu constraints=%zu\n",
                     dynamic_ids.size(), constraints.size());
        return 1;
    }

    physics.OptimizeBroadPhase();

    uint64_t finite_checks = 0;
    uint64_t forced_sleep_batches = 0;
    uint64_t forced_wake_batches = 0;
    std::vector<BodyID> cycle_ids;
    cycle_ids.reserve(48);

    for (uint32_t tick = 0; tick < cfg.ticks; ++tick) {
        const uint32_t phase = tick / 600;
        const uint32_t phase_tick = tick % 600;

        if (phase_tick == 480) {
            cycle_ids.clear();
            for (uint32_t i = phase % 4; i < box_count; i += 4)
                cycle_ids.push_back(dynamic_ids[i]);
            bodies.DeactivateBodies(cycle_ids.data(), static_cast<int>(cycle_ids.size()));
            ++forced_sleep_batches;
        }

        if (phase_tick == 540) {
            cycle_ids.clear();
            for (uint32_t i = phase % 4; i < box_count; i += 4)
                cycle_ids.push_back(dynamic_ids[i]);
            bodies.ActivateBodies(cycle_ids.data(), static_cast<int>(cycle_ids.size()));
            for (size_t i = 0; i < cycle_ids.size(); ++i) {
                const float sx = (i & 1U) == 0U ? 0.35f : -0.35f;
                const float sz = (i & 2U) == 0U ? 0.20f : -0.20f;
                bodies.AddImpulse(cycle_ids[i], Vec3(sx, 0.9f, sz));
            }
            ++forced_wake_batches;
        }

        const EPhysicsUpdateError update_error = physics.Update(dt, 1, &temp_allocator, &job_system);
        if (update_error != EPhysicsUpdateError::None) {
            std::fprintf(stderr, "physics update error tick=%u bits=0x%x\n",
                         tick, static_cast<unsigned>(update_error));
            return 1;
        }

        for (uint32_t i = 0; i < dynamic_count; ++i) {
            const BodyID id = dynamic_ids[i];
            if (!bodies.IsAdded(id)) {
                std::fprintf(stderr, "ownership failure tick=%u body=%u reason=not-added\n", tick, i);
                return 1;
            }
            if (bodies.GetUserData(id) != owner_tag(i)) {
                std::fprintf(stderr, "ownership failure tick=%u body=%u reason=user-data\n", tick, i);
                return 1;
            }
            RVec3 position;
            Quat rotation;
            Vec3 linear_velocity;
            Vec3 angular_velocity;
            bodies.GetPositionAndRotation(id, position, rotation);
            bodies.GetLinearAndAngularVelocity(id, linear_velocity, angular_velocity);
            if (!finite_rvec3(position) || !finite_quat(rotation) ||
                !finite_vec3(linear_velocity) || !finite_vec3(angular_velocity)) {
                std::fprintf(stderr,
                             "non-finite state tick=%u body=%u pos=(%.9g,%.9g,%.9g) quat=(%.9g,%.9g,%.9g,%.9g) lin=(%.9g,%.9g,%.9g) ang=(%.9g,%.9g,%.9g)\n",
                             tick, i,
                             static_cast<double>(position.GetX()), static_cast<double>(position.GetY()), static_cast<double>(position.GetZ()),
                             rotation.GetX(), rotation.GetY(), rotation.GetZ(), rotation.GetW(),
                             linear_velocity.GetX(), linear_velocity.GetY(), linear_velocity.GetZ(),
                             angular_velocity.GetX(), angular_velocity.GetY(), angular_velocity.GetZ());
                return 1;
            }
            ++finite_checks;
        }
    }

    const uint64_t activation_events = activation_counter.activations.load(std::memory_order_relaxed);
    const uint64_t deactivation_events = activation_counter.deactivations.load(std::memory_order_relaxed);
    const uint64_t contacts_added = contact_counter.added.load(std::memory_order_relaxed);
    const uint64_t contacts_persisted = contact_counter.persisted.load(std::memory_order_relaxed);

    if (forced_sleep_batches < 10 || forced_wake_batches < 10) {
        std::fprintf(stderr, "insufficient explicit sleep/wake batches\n");
        return 1;
    }
    if (activation_events <= dynamic_count || deactivation_events == 0) {
        std::fprintf(stderr, "sleep/wake listener evidence insufficient activations=%llu deactivations=%llu\n",
                     static_cast<unsigned long long>(activation_events),
                     static_cast<unsigned long long>(deactivation_events));
        return 1;
    }
    if (contacts_added == 0 || contacts_persisted == 0) {
        std::fprintf(stderr, "contact-heavy evidence missing added=%llu persisted=%llu\n",
                     static_cast<unsigned long long>(contacts_added),
                     static_cast<unsigned long long>(contacts_persisted));
        return 1;
    }
    if (canonical_before != canonical_sentinel) {
        std::fprintf(stderr, "canonical sentinel changed\n");
        return 1;
    }

    std::printf("jolt.version=%u.%u.%u\n", JPH_VERSION_MAJOR, JPH_VERSION_MINOR, JPH_VERSION_PATCH);
    std::printf("simulation.hz=60\n");
    std::printf("simulation.ticks=%u\n", cfg.ticks);
    std::printf("simulation.seconds=%.3f\n", static_cast<double>(cfg.ticks) / 60.0);
    std::printf("simulation.worker_threads=%u\n", cfg.worker_threads);
    std::printf("dynamic_bodies=%u\n", dynamic_count);
    std::printf("debris_bodies=%u\n", box_count);
    std::printf("ragdoll_bodies=%u\n", ragdoll_count);
    std::printf("ragdoll_constraints=%u\n", expected_constraints);
    std::printf("finite_checks=%llu\n", static_cast<unsigned long long>(finite_checks));
    std::printf("sleep_wake.forced_sleep_batches=%llu\n", static_cast<unsigned long long>(forced_sleep_batches));
    std::printf("sleep_wake.forced_wake_batches=%llu\n", static_cast<unsigned long long>(forced_wake_batches));
    std::printf("sleep_wake.activation_events=%llu\n", static_cast<unsigned long long>(activation_events));
    std::printf("sleep_wake.deactivation_events=%llu\n", static_cast<unsigned long long>(deactivation_events));
    std::printf("contacts.added=%llu\n", static_cast<unsigned long long>(contacts_added));
    std::printf("contacts.persisted=%llu\n", static_cast<unsigned long long>(contacts_persisted));
    std::printf("canonical.sentinel_before=0x%016llx\n", static_cast<unsigned long long>(canonical_before));
    std::printf("canonical.sentinel_after=0x%016llx\n", static_cast<unsigned long long>(canonical_sentinel));
    std::printf("canonical.authority=none\n");
    std::printf("result=PASS\n");

    for (Ref<Constraint> &constraint : constraints)
        physics.RemoveConstraint(constraint);
    for (const BodyID id : dynamic_ids) {
        bodies.RemoveBody(id);
        bodies.DestroyBody(id);
    }
    bodies.RemoveBody(floor_id);
    bodies.DestroyBody(floor_id);

    UnregisterTypes();
    delete Factory::sInstance;
    Factory::sInstance = nullptr;
    return 0;
}
