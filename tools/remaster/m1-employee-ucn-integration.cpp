/**
 * @file
 * @brief M1-only EmployeeId / CharacterUcn allocator and wire fixtures.
 *
 * Injected into ufotestall only with UFOAI_M1_EMPLOYEE_UCN_TESTS=ON.
 * The sealed src/tests/CMakeLists.txt remains untouched.
 */

#include "../../src/tests/test_shared.h"
#include "../../src/client/client.h"
#include "../../src/client/cl_team.h"

#include <cstdint>
#include <limits>

namespace {

class UcnCounterGuard {
public:
	UcnCounterGuard() : previous(cls.nextUniqueCharacterNumber) {}
	~UcnCounterGuard() { cls.nextUniqueCharacterNumber = previous; }

private:
	int previous;
};

TEST(M1EmployeeUcnTest, ReconcilesLoadedUcnMonotonically)
{
	UcnCounterGuard guard;
	const int maxUcn = std::numeric_limits<std::int16_t>::max();

	cls.nextUniqueCharacterNumber = 7;

	EXPECT_TRUE(CL_ReconcileCharacterUCN(41));
	EXPECT_EQ(42, cls.nextUniqueCharacterNumber);

	EXPECT_TRUE(CL_ReconcileCharacterUCN(12));
	EXPECT_EQ(42, cls.nextUniqueCharacterNumber);

	EXPECT_FALSE(CL_ReconcileCharacterUCN(-1));
	EXPECT_EQ(42, cls.nextUniqueCharacterNumber);

	EXPECT_FALSE(CL_ReconcileCharacterUCN(maxUcn + 1));
	EXPECT_EQ(42, cls.nextUniqueCharacterNumber);

	EXPECT_TRUE(CL_ReconcileCharacterUCN(maxUcn));
	EXPECT_EQ(maxUcn + 1, cls.nextUniqueCharacterNumber);
}

TEST(M1EmployeeUcnTest, PreservesSigned16BitWireDomain)
{
	const int maxUcn = std::numeric_limits<std::int16_t>::max();
	const int firstInvalid = maxUcn + 1;

	EXPECT_TRUE(CL_IsCharacterUCNWireRepresentable(0));
	EXPECT_TRUE(CL_IsCharacterUCNWireRepresentable(maxUcn));
	EXPECT_FALSE(CL_IsCharacterUCNWireRepresentable(-1));
	EXPECT_FALSE(CL_IsCharacterUCNWireRepresentable(firstInvalid));

	dbuffer msg;
	NET_WriteShort(&msg, maxUcn);
	NET_WriteShort(&msg, firstInvalid);

	EXPECT_EQ(maxUcn, NET_ReadShort(&msg));
	EXPECT_EQ(std::numeric_limits<std::int16_t>::min(), NET_ReadShort(&msg));
}

} // namespace
