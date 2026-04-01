-- Custom triggers for leave dashboard to setup using albemic migrate --
------------------------------------------------------------------------
-- reset_and_check_leaves_fn will reset the leave counts for an employee
-- if the year has changed and also check if the leave limits are exceeded 
-- before inserting a new leave record.
CREATE OR REPLACE FUNCTION reset_and_check_leaves_fn() RETURNS TRIGGER AS $$ BEGIN
UPDATE employee
SET casual_leaves = 0,
    gazzetted_leaves = 0,
    compensatory_leaves = 0,
    without_pay_leaves = 0,
    half_casual_leaves = 0,
    last_reset_year = EXTRACT(
        YEAR
        FROM NOW()
    )::TEXT
WHERE id = NEW.employee_id
    AND last_reset_year < EXTRACT(
        YEAR
        FROM NOW()
    )::TEXT;
-- Check if the leave limits are exceeded before inserting a new leave record
IF NEW.leave_type = 'CASUAL'
AND (
    SELECT casual_leaves
    FROM employee
    WHERE id = NEW.employee_id
) >= 8 THEN RAISE EXCEPTION 'Casual leave limit exceeded';
END IF;
IF NEW.leave_type = 'GAZZETTED'
AND (
    SELECT gazzetted_leaves
    FROM employee
    WHERE id = NEW.employee_id
) >= 4 THEN RAISE EXCEPTION 'Gazzetted leave limit exceeded';
END IF;
RETURN NEW;
END;
$$ LANGUAGE plpgsql;
-- Create the trigger to call the function before inserting a new leave record
DROP TRIGGER IF EXISTS reset_and_check_leaves ON "leave";
CREATE TRIGGER reset_and_check_leaves BEFORE
INSERT ON "leave" FOR EACH ROW EXECUTE FUNCTION reset_and_check_leaves_fn();
-- increment_leave_counts_fn will increment the leave counts for an employee based
-- on the leave type after inserting a new leave record.
CREATE OR REPLACE FUNCTION increment_leave_counts_fn() RETURNS TRIGGER AS $$ BEGIN IF NEW.leave_type = 'CASUAL' THEN
UPDATE employee
SET casual_leaves = casual_leaves + 1
WHERE id = NEW.employee_id;
ELSIF NEW.leave_type = 'GAZZETTED' THEN
UPDATE employee
SET gazzetted_leaves = gazzetted_leaves + 1
WHERE id = NEW.employee_id;
ELSIF NEW.leave_type = 'COMPENSATORY' THEN
UPDATE employee
SET compensatory_leaves = compensatory_leaves + 1
WHERE id = NEW.employee_id;
ELSIF NEW.leave_type = 'WITHOUT_PAY' THEN
UPDATE employee
SET without_pay_leaves = without_pay_leaves + 1
WHERE id = NEW.employee_id;
ELSIF NEW.leave_type = 'HALF_CL' THEN
UPDATE employee
SET half_casual_leaves = half_casual_leaves + 1
WHERE id = NEW.employee_id;
END IF;
RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS increment_leave_counts ON "leave";
CREATE TRIGGER increment_leave_counts
AFTER
INSERT ON "leave" FOR EACH ROW EXECUTE FUNCTION increment_leave_counts_fn();
-- cleanup_old_leaves_fn will delete leave records that are older than 3 months
-- after inserting a new leave record.
CREATE OR REPLACE FUNCTION cleanup_old_leaves_fn() RETURNS TRIGGER AS $$ BEGIN
DELETE FROM "leave"
WHERE created_at < NOW() - INTERVAL '3 months';
RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS cleanup_old_leaves ON "leave";
CREATE TRIGGER cleanup_old_leaves
AFTER
INSERT ON "leave" FOR EACH ROW EXECUTE FUNCTION cleanup_old_leaves_fn();
------------------------------------------------------------------------