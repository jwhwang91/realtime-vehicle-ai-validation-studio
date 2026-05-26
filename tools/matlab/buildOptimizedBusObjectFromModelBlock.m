function [busObj, report] = buildOptimizedBusObjectFromModelBlock(blockPath, busObjectName, varargin)
% buildOptimizedBusObjectFromModelBlock
%
% Public-safe portfolio mock MATLAB utility.
%
% This script demonstrates the MBD-side preparation needed when a
% MATLAB/Simulink auto-code-generation workflow must expose AI model input
% signals as a stable, optimized, externally accessible generated C struct.
%
% Core workflow demonstrated by this mock utility:
%
%   1. Automatically find non-virtual Bus Creator blocks under a Simulink
%      model/subsystem block path.
%
%   2. Inspect the connected input signals and resolve their compiled data
%      types.
%
%   3. Generate an optimized Simulink.Bus object in the MATLAB base workspace
%      by sorting bus elements from larger data types to smaller data types.
%      This top-down ordering helps reduce padding/alignment inefficiency in
%      generated C struct layouts.
%
%   4. Optionally apply the same optimized signal order back into the
%      Simulink model by reconnecting the Bus Creator input ports in the
%      optimized order.
%
% Why this matters:
%   In a constrained runtime access environment, such as CAN-FD/XCP-style
%   measurement instead of higher-throughput Ethernet measurement, the embedded
%   signal interface must be prepared carefully. If AI model inputs are exposed
%   through generated global/external bus structures, the generated struct
%   should be stable, compact, and easy to map to measurement/calibration
%   metadata.
%
% Important:
%   This is a sanitized mock script for portfolio demonstration only.
%   It does not include proprietary model paths, real signal names, production
%   A2L/ELF metadata, or company-specific code-generation settings.
%
% Example:
%   [busObj, report] = buildOptimizedBusObjectFromModelBlock( ...
%       "demo_model/AI_Input_Interface", ...
%       "AI_Input_OptimizedBus", ...
%       "ApplyToModel", true);
%
% Optional name-value arguments:
%   "AssignToBase"       true/false
%       Assign the generated Simulink.Bus object to the MATLAB base workspace.
%
%   "ApplyToModel"       true/false
%       Reorder the Bus Creator input connections in the Simulink model to
%       match the optimized bus element order.
%
%   "CreateBackup"       true/false
%       Save a backup copy of the model before applying line changes.
%
%   "Verbose"            true/false
%       Print a report.
%
% Output:
%   busObj  - optimized Simulink.Bus object
%   report  - table describing original order, optimized order, type rank,
%             source blocks, and Bus Creator paths

arguments
    blockPath (1,1) string
    busObjectName (1,1) string = "AI_Input_OptimizedBus"
end

arguments (Repeating)
    varargin
end

p = inputParser;
addParameter(p, "AssignToBase", true, @(x)islogical(x) || isnumeric(x));
addParameter(p, "ApplyToModel", true, @(x)islogical(x) || isnumeric(x));
addParameter(p, "CreateBackup", true, @(x)islogical(x) || isnumeric(x));
addParameter(p, "Verbose", true, @(x)islogical(x) || isnumeric(x));
parse(p, varargin{:});

assignToBase = logical(p.Results.AssignToBase);
applyToModel = logical(p.Results.ApplyToModel);
createBackup = logical(p.Results.CreateBackup);
verbose = logical(p.Results.Verbose);

modelName = extractBefore(blockPath + "/", "/");
modelName = char(modelName);

if isempty(modelName)
    error("Invalid blockPath. Expected format: model/subsystem/block");
end

if ~bdIsLoaded(modelName)
    try
        load_system(modelName);
    catch ME
        error("Could not load model '%s'. Original error: %s", modelName, ME.message);
    end
end

try
    set_param(modelName, "SimulationCommand", "update");
catch ME
    warning("Diagram update failed. Compiled data types may be incomplete: %s", ME.message);
end

if applyToModel && createBackup
    createModelBackup(modelName);
end

busCreators = find_system( ...
    char(blockPath), ...
    "LookUnderMasks", "all", ...
    "FollowLinks", "on", ...
    "BlockType", "BusCreator");

if isempty(busCreators)
    warning("No Bus Creator blocks found under: %s", blockPath);
    busObj = Simulink.Bus;
    busObj.Elements = Simulink.BusElement.empty;
    report = table;
    return;
end

nonVirtualBusCreators = {};
for i = 1:numel(busCreators)
    blk = busCreators{i};
    if isLikelyNonVirtualBusCreator(blk)
        nonVirtualBusCreators{end+1} = blk; %#ok<AGROW>
    end
end

% Some Simulink versions or mock/demo models may not expose a clear
% non-virtual parameter. In that case, use all Bus Creator blocks so the
% demo utility remains useful.
if isempty(nonVirtualBusCreators)
    nonVirtualBusCreators = busCreators;
end

allRows = [];
busObjectElements = Simulink.BusElement.empty;

for b = 1:numel(nonVirtualBusCreators)
    busBlk = nonVirtualBusCreators{b};
    rows = collectBusCreatorInputs(busBlk);

    if isempty(rows)
        continue;
    end

    busTable = struct2table(rows);
    busTable.Name = matlab.lang.makeUniqueStrings(cellstr(busTable.Name));
    busTable.Name = string(busTable.Name);
    busTable.OriginalOrder = (1:height(busTable)).';
    busTable.OptimizedOrder = zeros(height(busTable), 1);

    % Larger data types first, then original order for deterministic behavior.
    busTable = sortrows(busTable, ["ByteRank", "OriginalOrder"], ["descend", "ascend"]);
    busTable.OptimizedOrder = (1:height(busTable)).';

    if applyToModel
        applyOptimizedOrderToBusCreator(busBlk, busTable);
    end

    elements = createBusElementsFromTable(busTable);
    busObjectElements = [busObjectElements; elements(:)]; %#ok<AGROW>

    if isempty(allRows)
        allRows = busTable;
    else
        allRows = [allRows; busTable]; %#ok<AGROW>
    end
end

if isempty(allRows)
    warning("No connected input signals were discovered.");
    busObj = Simulink.Bus;
    busObj.Elements = Simulink.BusElement.empty;
    report = table;
    return;
end

busObj = Simulink.Bus;
busObj.Description = sprintf( ...
    "Public-safe mock optimized bus object generated from %s", ...
    blockPath);
busObj.Elements = busObjectElements;

report = allRows;

if assignToBase
    assignin("base", char(busObjectName), busObj);
end

if verbose
    fprintf("\nGenerated optimized bus object: %s\n", busObjectName);
    fprintf("Source block path: %s\n", blockPath);
    fprintf("Bus Creators processed: %d\n", numel(nonVirtualBusCreators));
    fprintf("Signals discovered: %d\n", height(report));
    fprintf("Applied optimized order to model: %d\n\n", applyToModel);
    disp(report(:, ["BusCreator", "OriginalOrder", "OptimizedOrder", "Name", "OriginalName", "DataType", "ByteRank", "SourceBlock"]));
end

try
    set_param(modelName, "SimulationCommand", "update");
catch
end

end

% ========================================================================
% Bus Creator collection / model rewrite
% ========================================================================

function rows = collectBusCreatorInputs(busBlk)
rows = struct( ...
    "Name", {}, ...
    "OriginalName", {}, ...
    "DataType", {}, ...
    "Dimensions", {}, ...
    "Complexity", {}, ...
    "SourceBlock", {}, ...
    "SourcePort", {}, ...
    "SourcePortHandle", {}, ...
    "SourceLineHandle", {}, ...
    "DestinationPortHandle", {}, ...
    "BusCreator", {}, ...
    "ByteRank", {});

ph = get_param(busBlk, "PortHandles");
inPorts = ph.Inport;

for k = 1:numel(inPorts)
    dstPort = inPorts(k);
    lineHandle = get_param(dstPort, "Line");

    if lineHandle == -1
        continue;
    end

    srcPort = get_param(lineHandle, "SrcPortHandle");

    if srcPort == -1
        continue;
    end

    rawName = get_param(lineHandle, "Name");
    if isempty(rawName)
        rawName = inferSignalNameFromSource(srcPort);
    end

    cleanName = matlab.lang.makeValidName(rawName);

    dataType = getCompiledDataTypeSafe(srcPort);
    dims = getCompiledDimensionsSafe(srcPort);
    complexity = getCompiledComplexitySafe(srcPort);
    srcBlock = get_param(srcPort, "Parent");
    srcPortNumber = get_param(srcPort, "PortNumber");

    rows(end+1).Name = string(cleanName); %#ok<AGROW>
    rows(end).OriginalName = string(rawName);
    rows(end).DataType = string(dataType);
    rows(end).Dimensions = string(dims);
    rows(end).Complexity = string(complexity);
    rows(end).SourceBlock = string(srcBlock);
    rows(end).SourcePort = double(srcPortNumber);
    rows(end).SourcePortHandle = double(srcPort);
    rows(end).SourceLineHandle = double(lineHandle);
    rows(end).DestinationPortHandle = double(dstPort);
    rows(end).BusCreator = string(busBlk);
    rows(end).ByteRank = dataTypeByteRank(dataType);
end
end

function applyOptimizedOrderToBusCreator(busBlk, busTable)
% Reconnect Bus Creator inputs so the visual/model order matches the
% optimized bus object order. This is the key step that makes the ordering
% affect subsequent code generation.
%
% Strategy:
%   1. Capture source port handles and signal names from the original lines.
%   2. Delete existing lines into the Bus Creator.
%   3. Ensure the Bus Creator has the correct number of input ports.
%   4. Reconnect sources to Bus Creator input ports in optimized order.
%
% Notes:
%   - add_line with port handles is supported in typical Simulink workflows.
%   - Existing branch lines and complex routing may need project-specific
%     handling in production. This mock keeps the algorithm understandable.

parentSystem = get_param(busBlk, "Parent");
n = height(busTable);

% Capture source port handles and signal names before deleting lines.
sourcePorts = busTable.SourcePortHandle;
signalNames = busTable.OriginalName;

% Delete old lines connected to this Bus Creator.
for i = 1:n
    lineHandle = busTable.SourceLineHandle(i);
    try
        if lineHandle ~= -1 && ishandle(lineHandle)
            delete_line(lineHandle);
        end
    catch
        % Continue so the demo utility does not stop on a partially routed
        % or already deleted line.
    end
end

% Make sure the Bus Creator has the exact number of inputs.
try
    set_param(busBlk, "Inputs", num2str(n));
catch ME
    warning("Could not update Bus Creator input count for %s: %s", busBlk, ME.message);
end

% Refresh port handles after changing input count.
ph = get_param(busBlk, "PortHandles");
dstPorts = ph.Inport;

if numel(dstPorts) < n
    warning("Bus Creator %s has fewer ports than expected after update.", busBlk);
    n = min(n, numel(dstPorts));
end

% Reconnect in optimized order.
for i = 1:n
    src = sourcePorts(i);
    dst = dstPorts(i);

    try
        newLine = add_line(parentSystem, src, dst, "autorouting", "on");

        % Preserve readable line names where possible.
        sigName = char(signalNames(i));
        if ~isempty(sigName)
            try
                set_param(newLine, "Name", sigName);
            catch
            end
        end
    catch ME
        warning("Could not reconnect optimized signal order at %s input %d: %s", busBlk, i, ME.message);
    end
end

try
    Simulink.BlockDiagram.arrangeSystem(parentSystem);
catch
end

end

function elements = createBusElementsFromTable(busTable)
elements(height(busTable), 1) = Simulink.BusElement;

for i = 1:height(busTable)
    e = Simulink.BusElement;
    e.Name = char(busTable.Name(i));
    e.DataType = char(busTable.DataType(i));
    e.Description = sprintf( ...
        "Mock generated from %s | original signal: %s | optimized order: %d", ...
        busTable.SourceBlock(i), ...
        busTable.OriginalName(i), ...
        busTable.OptimizedOrder(i));

    dimsText = char(busTable.Dimensions(i));
    dimsNumeric = parseDimensions(dimsText);
    if ~isempty(dimsNumeric)
        e.Dimensions = dimsNumeric;
    end

    elements(i) = e;
end
end

% ========================================================================
% Helper functions
% ========================================================================

function tf = isLikelyNonVirtualBusCreator(blockPath)
tf = false;

candidateParams = { ...
    "OutputAsNonVirtualBus", ...
    "OutputAsNonvirtualBus", ...
    "NonVirtualBus" ...
};

for i = 1:numel(candidateParams)
    try
        value = get_param(blockPath, candidateParams{i});
        if strcmpi(value, "on") || strcmpi(value, "true") || isequal(value, 1)
            tf = true;
            return;
        end
    catch
    end
end

try
    outDataType = get_param(blockPath, "OutDataTypeStr");
    if startsWith(string(outDataType), "Bus:", "IgnoreCase", true)
        tf = true;
    end
catch
end

end

function createModelBackup(modelName)
try
    modelFile = which(modelName);
    if isempty(modelFile)
        return;
    end

    [folder, name, ext] = fileparts(modelFile);
    stamp = datestr(now, "yyyymmdd_HHMMSS");
    backupFile = fullfile(folder, sprintf("%s_backup_%s%s", name, stamp, ext));
    copyfile(modelFile, backupFile);
    fprintf("Created model backup: %s\n", backupFile);
catch ME
    warning("Could not create model backup: %s", ME.message);
end
end

function name = inferSignalNameFromSource(srcPort)
try
    srcBlock = get_param(srcPort, "Parent");
    srcName = get_param(srcBlock, "Name");
    portNumber = get_param(srcPort, "PortNumber");
    name = sprintf("%s_out%d", srcName, portNumber);
catch
    name = "unnamed_signal";
end
end

function dataType = getCompiledDataTypeSafe(portHandle)
dataType = "double";

try
    dataType = string(get_param(portHandle, "CompiledPortDataType"));
    if strlength(dataType) > 0
        return;
    end
catch
end

try
    dataTypes = get_param(portHandle, "CompiledPortDataTypes");
    if isstruct(dataTypes) && isfield(dataTypes, "Outport")
        dataType = string(dataTypes.Outport);
        return;
    end
catch
end

dataType = "double";
end

function dims = getCompiledDimensionsSafe(portHandle)
dims = "1";

try
    d = get_param(portHandle, "CompiledPortDimensions");
    if isnumeric(d)
        if numel(d) == 1
            dims = string(d);
        else
            dims = join(string(d(:).'), "x");
        end
        return;
    end
catch
end

dims = "1";
end

function complexity = getCompiledComplexitySafe(portHandle)
complexity = "real";
try
    c = get_param(portHandle, "CompiledPortComplexSignal");
    if isequal(c, 1) || strcmpi(string(c), "on")
        complexity = "complex";
    end
catch
end
end

function rank = dataTypeByteRank(dataType)
dt = lower(strtrim(char(dataType)));

switch dt
    case {"double", "uint64", "int64", "ulonglong", "longlong"}
        rank = 8;
    case {"single", "uint32", "int32", "ulong", "long"}
        rank = 4;
    case {"uint16", "int16", "ushort", "short"}
        rank = 2;
    case {"boolean", "bool", "uint8", "int8", "ubyte", "sbyte", "char"}
        rank = 1;
    otherwise
        token = regexp(dt, "fixdt\([^,]+,\s*(\d+)", "tokens", "once");
        if ~isempty(token)
            wordLength = str2double(token{1});
            rank = max(1, ceil(wordLength / 8));
        else
            rank = 4;
        end
end
end

function dims = parseDimensions(text)
text = strtrim(char(text));
dims = [];

if isempty(text)
    return;
end

parts = regexp(text, "[x,\s]+", "split");
values = str2double(parts);
values = values(~isnan(values));

if ~isempty(values)
    dims = values;
end
end
