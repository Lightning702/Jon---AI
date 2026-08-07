#include "BlackHolePass.hpp"

#include "../core/Log.hpp"
#include "SkyCommon.hpp"

#include <string>

namespace sf {
namespace {

const char* const kBlackHoleFragmentBody = R"GLSL(
in vec2 vScreenUv;
out vec4 fragColor;

uniform vec3 uCameraRight;
uniform vec3 uCameraUp;
uniform vec3 uCameraForward;
uniform vec3 uCameraPosition;
uniform float uTanHalfFieldOfView;
uniform float uAspectRatio;
uniform float uSpin;
uniform float uDiskInnerRadius;
uniform float uDiskOuterRadius;
uniform float uDiskInnerTemperature;
uniform float uDiskThickness;
uniform float uDiskOpacity;
uniform float uDiskBrightness;
uniform float uJetStrength;
uniform float uAccretionRate;
uniform float uTime;
uniform float uExposure;
uniform float uStepFraction;
uniform int uMaximumSteps;
uniform int uIntegratorOrder;
uniform int uSkyDetail;
uniform vec2 uPixelJitter;

const float kEscapeRadius = 4200.0;

float horizonRadiusOf(float spin) {
    return 1.0 + sqrt(max(1.0 - spin * spin, 0.0));
}

vec3 boyerLindquistToCartesian(float radius, float theta, float phi, float spin) {
    float oblate = sqrt(radius * radius + spin * spin);
    float sinTheta = sin(theta);
    return vec3(oblate * sinTheta * cos(phi), radius * cos(theta), oblate * sinTheta * sin(phi));
}

void geodesicDerivatives(float radius, float theta, float momentumRadial, float momentumPolar,
                         float energy, float angularMomentum, float spin,
                         out float derivativeRadius, out float derivativeTheta, out float derivativePhi,
                         out float derivativeMomentumRadial, out float derivativeMomentumPolar) {
    float spinSquared = spin * spin;
    float delta = radius * radius - 2.0 * radius + spinSquared;
    float safeDelta = abs(delta) < 1.0e-5 ? (delta >= 0.0 ? 1.0e-5 : -1.0e-5) : delta;
    float sinTheta = sin(theta);
    float absoluteSine = max(abs(sinTheta), 1.0e-4);
    float signedSine = sinTheta < 0.0 ? -absoluteSine : absoluteSine;
    float cosTheta = cos(theta);

    float radialPotential = (radius * radius + spinSquared) * energy - spin * angularMomentum;
    float radialPotentialDerivative = 2.0 * radius * energy;
    float deltaDerivative = 2.0 * radius - 2.0;

    float polarTerm = angularMomentum / signedSine - spin * energy * signedSine;
    float polarTermDerivative = -angularMomentum * cosTheta / (signedSine * signedSine) - spin * energy * cosTheta;

    derivativeRadius = safeDelta * momentumRadial;
    derivativeTheta = momentumPolar;
    derivativePhi = spin * radialPotential / safeDelta + angularMomentum / (signedSine * signedSine) - spin * energy;

    float potentialQuotientDerivative =
        (2.0 * radialPotential * radialPotentialDerivative * safeDelta - radialPotential * radialPotential * deltaDerivative) /
        (safeDelta * safeDelta);
    derivativeMomentumRadial = -0.5 * (deltaDerivative * momentumRadial * momentumRadial - potentialQuotientDerivative);
    derivativeMomentumPolar = -polarTerm * polarTermDerivative;
}

float pageThorneFlux(float radius, float innerRadius, float spin) {
    float x = sqrt(max(radius, 1.0e-4));
    float x0 = sqrt(max(innerRadius, 1.0e-4));
    if (x <= x0) return 0.0;

    float third = acos(clamp(spin, -1.0, 1.0)) / 3.0;
    float x1 = 2.0 * cos(third - 1.0471975512);
    float x2 = 2.0 * cos(third + 1.0471975512);
    float x3 = -2.0 * cos(third);

    float denominator = x * x * x - 3.0 * x + 2.0 * spin;
    if (denominator <= 1.0e-5) return 0.0;

    float term1 = 3.0 * (x1 - spin) * (x1 - spin) / (x1 * (x1 - x2) * (x1 - x3));
    float term2 = 3.0 * (x2 - spin) * (x2 - spin) / (x2 * (x2 - x1) * (x2 - x3));
    float term3 = 3.0 * (x3 - spin) * (x3 - spin) / (x3 * (x3 - x1) * (x3 - x2));

    float bracket = x - x0 - 1.5 * spin * log(x / x0);
    bracket -= term1 * log(max((x - x1) / (x0 - x1), 1.0e-6));
    bracket -= term2 * log(max((x - x2) / (x0 - x2), 1.0e-6));
    bracket -= term3 * log(max((x - x3) / (x0 - x3), 1.0e-6));

    float flux = bracket / (x * x * x * x * x * x * x * denominator) * 3.0;
    return max(flux, 0.0);
}

float diskTemperatureAt(float radius, float innerRadius, float innerTemperature, float spin) {
    float flux = pageThorneFlux(radius, innerRadius, spin);
    if (flux <= 0.0) return 0.0;
    float reference = pageThorneFlux(innerRadius * 1.3611111, innerRadius, spin);
    if (reference <= 0.0) return 0.0;
    return innerTemperature * pow(flux / reference, 0.25);
}

float limbDarkening(float cosineEmission) {
    float mu = clamp(cosineEmission, 0.0, 1.0);
    return (1.0 + 2.06 * mu) / 3.06;
}

float diskDensityPattern(float radius, float phi, float spin, float time) {
    float orbitalRate = 1.0 / (pow(max(radius, 1.0e-3), 1.5) + spin);
    float trailingPhi = phi - orbitalRate * time * 46.0;
    float logRadius = log(max(radius, 1.0e-3));

    float shear = orbitalRate * 1.5 / max(radius, 1.0e-3);
    float shearedPhi = trailingPhi + shear * logRadius * 220.0;

    vec2 azimuthal = vec2(cos(shearedPhi), sin(shearedPhi));
    vec3 coarse = vec3(azimuthal * (radius * 0.16), logRadius * 6.4);
    vec3 fine = vec3(azimuthal * (radius * 0.90), logRadius * 22.0);

    float filaments = skyFractal(coarse, 4);
    float fineStructure = skyFractal(fine, 3);
    float spiralWave = 0.5 + 0.5 * sin(shearedPhi * 2.0 + logRadius * 5.4);
    float turbulence = mix(filaments, fineStructure, 0.38);
    return clamp(0.30 + turbulence * 1.42 * (0.52 + 0.48 * spiralWave), 0.0, 2.0);
}

vec3 jetEmissionAt(vec3 position, float spin, float time) {
    float axialDistance = abs(position.y);
    if (axialDistance < 1.6 || axialDistance > 900.0) return vec3(0.0);
    float cylindrical = length(position.xz);
    float openingRadius = 0.55 + pow(axialDistance, 0.62) * 0.30;
    float profile = exp(-(cylindrical * cylindrical) / max(openingRadius * openingRadius, 1.0e-3));
    if (profile < 0.002) return vec3(0.0);

    float shockPhase = log(axialDistance + 1.0) * 5.5 - time * 0.65;
    float shockKnots = 0.55 + 0.45 * sin(shockPhase) * sin(shockPhase * 0.37 + 1.7);
    float filament = skyFractal(vec3(position.xz * 1.4, axialDistance * 0.35 - time * 0.4), 3);
    float attenuation = 1.0 / (1.0 + axialDistance * 0.055);

    vec3 innerColor = vec3(0.42, 0.72, 1.0);
    vec3 outerColor = vec3(0.85, 0.42, 1.0);
    vec3 tint = mix(innerColor, outerColor, clamp(axialDistance / 260.0, 0.0, 1.0));
    return tint * profile * shockKnots * (0.45 + filament) * attenuation * uJetStrength * 0.055;
}

void main() {
    vec2 normalizedScreen = (vScreenUv + uPixelJitter) * 2.0 - 1.0;
    vec3 viewDirection = normalize(uCameraForward +
                                   uCameraRight * (normalizedScreen.x * uTanHalfFieldOfView * uAspectRatio) +
                                   uCameraUp * (normalizedScreen.y * uTanHalfFieldOfView));

    float spin = clamp(uSpin, 0.0, 0.998);
    float spinSquared = spin * spin;
    vec3 cameraPosition = uCameraPosition;

    float planarSquared = cameraPosition.x * cameraPosition.x + cameraPosition.z * cameraPosition.z;
    float verticalSquared = cameraPosition.y * cameraPosition.y;
    float combined = planarSquared + verticalSquared - spinSquared;
    float radius = sqrt(max(0.5 * (combined + sqrt(max(combined * combined + 4.0 * spinSquared * verticalSquared, 0.0))), 1.0e-4));
    float theta = acos(clamp(cameraPosition.y / max(radius, 1.0e-4), -1.0, 1.0));
    float phi = atan(cameraPosition.z, cameraPosition.x);

    float sinTheta = max(sin(theta), 1.0e-4);
    float cosTheta = cos(theta);
    float sinPhi = sin(phi);
    float cosPhi = cos(phi);
    float oblate = sqrt(radius * radius + spinSquared);

    vec3 radialBasis = normalize(vec3((radius / oblate) * sinTheta * cosPhi, cosTheta, (radius / oblate) * sinTheta * sinPhi));
    vec3 polarBasis = normalize(vec3(oblate * cosTheta * cosPhi, -radius * sinTheta, oblate * cosTheta * sinPhi));
    vec3 azimuthBasis = vec3(-sinPhi, 0.0, cosPhi);

    vec3 incomingDirection = -viewDirection;
    vec3 localDirection = normalize(vec3(dot(incomingDirection, radialBasis),
                                         dot(incomingDirection, polarBasis),
                                         dot(incomingDirection, azimuthBasis)));

    float sigma = radius * radius + spinSquared * cosTheta * cosTheta;
    float delta = radius * radius - 2.0 * radius + spinSquared;
    if (delta <= 0.0) {
        fragColor = vec4(0.0, 0.0, 0.0, 1.0);
        return;
    }
    float metricA = (radius * radius + spinSquared) * (radius * radius + spinSquared) - spinSquared * delta * sinTheta * sinTheta;
    float frameDragging = 2.0 * spin * radius / max(metricA, 1.0e-6);
    float lapse = sqrt(max(sigma * delta / max(metricA, 1.0e-6), 1.0e-9));

    float momentumRadial = localDirection.x * sqrt(sigma / delta);
    float momentumPolar = localDirection.y * sqrt(sigma);
    float angularMomentum = localDirection.z * sinTheta * sqrt(metricA / max(sigma, 1.0e-6));
    float energy = lapse + frameDragging * angularMomentum;

    float horizon = horizonRadiusOf(spin) * 1.0009;
    float diskInner = max(uDiskInnerRadius, horizon + 0.05);

    vec3 accumulated = vec3(0.0);
    vec3 previousCartesian = boyerLindquistToCartesian(radius, theta, phi, spin);
    float previousCosine = cos(theta);
    float previousRadius = radius;
    float previousPhi = phi;
    bool escaped = false;
    bool captured = false;
    bool diskHit = false;
    vec3 diskColor = vec3(0.0);
    vec3 escapeDirection = viewDirection;

    for (int iteration = 0; iteration < uMaximumSteps; ++iteration) {
        float derivativeRadius, derivativeTheta, derivativePhi, derivativeMomentumRadial, derivativeMomentumPolar;
        geodesicDerivatives(radius, theta, momentumRadial, momentumPolar, energy, angularMomentum, spin,
                            derivativeRadius, derivativeTheta, derivativePhi,
                            derivativeMomentumRadial, derivativeMomentumPolar);

        float radialSpeed = abs(derivativeRadius) + 1.0e-6;
        float targetAdvance = uStepFraction * (radius + 1.0);
        float stepSize = targetAdvance / radialSpeed;
        float polarSpeed = abs(derivativeTheta) + 1.0e-6;
        stepSize = min(stepSize, 0.045 / polarSpeed);
        float azimuthSpeed = abs(derivativePhi) + 1.0e-6;
        stepSize = min(stepSize, 0.075 / azimuthSpeed);
        stepSize = -stepSize;

        float r1 = radius;
        float t1 = theta;
        float pr1 = momentumRadial;
        float pt1 = momentumPolar;
        float dr1 = derivativeRadius;
        float dt1 = derivativeTheta;
        float dp1 = derivativePhi;
        float dpr1 = derivativeMomentumRadial;
        float dpt1 = derivativeMomentumPolar;

        float dr2, dt2, dp2, dpr2, dpt2;
        geodesicDerivatives(r1 + 0.5 * stepSize * dr1, t1 + 0.5 * stepSize * dt1,
                            pr1 + 0.5 * stepSize * dpr1, pt1 + 0.5 * stepSize * dpt1,
                            energy, angularMomentum, spin, dr2, dt2, dp2, dpr2, dpt2);

        if (uIntegratorOrder <= 1) {
            radius = r1 + stepSize * dr2;
            theta = t1 + stepSize * dt2;
            phi = phi + stepSize * dp2;
            momentumRadial = pr1 + stepSize * dpr2;
            momentumPolar = pt1 + stepSize * dpt2;
        } else {
            float dr3, dt3, dp3, dpr3, dpt3;
            geodesicDerivatives(r1 + 0.5 * stepSize * dr2, t1 + 0.5 * stepSize * dt2,
                                pr1 + 0.5 * stepSize * dpr2, pt1 + 0.5 * stepSize * dpt2,
                                energy, angularMomentum, spin, dr3, dt3, dp3, dpr3, dpt3);

            float dr4, dt4, dp4, dpr4, dpt4;
            geodesicDerivatives(r1 + stepSize * dr3, t1 + stepSize * dt3,
                                pr1 + stepSize * dpr3, pt1 + stepSize * dpt3,
                                energy, angularMomentum, spin, dr4, dt4, dp4, dpr4, dpt4);

            float sixth = stepSize / 6.0;
            radius = r1 + sixth * (dr1 + 2.0 * dr2 + 2.0 * dr3 + dr4);
            theta = t1 + sixth * (dt1 + 2.0 * dt2 + 2.0 * dt3 + dt4);
            phi = phi + sixth * (dp1 + 2.0 * dp2 + 2.0 * dp3 + dp4);
            momentumRadial = pr1 + sixth * (dpr1 + 2.0 * dpr2 + 2.0 * dpr3 + dpr4);
            momentumPolar = pt1 + sixth * (dpt1 + 2.0 * dpt2 + 2.0 * dpt3 + dpt4);
        }

        if (radius <= horizon) {
            captured = true;
            break;
        }

        vec3 currentCartesian = boyerLindquistToCartesian(radius, theta, phi, spin);
        if (uJetStrength > 0.001) {
            float segmentLength = length(currentCartesian - previousCartesian);
            accumulated += jetEmissionAt((currentCartesian + previousCartesian) * 0.5, spin, uTime) *
                           min(segmentLength, 6.0);
        }

        float currentCosine = cos(theta);
        if (previousCosine * currentCosine < 0.0 && !diskHit) {
            float blend = previousCosine / max(previousCosine - currentCosine, 1.0e-6);
            float crossingRadius = mix(previousRadius, radius, clamp(blend, 0.0, 1.0));
            float crossingPhi = mix(previousPhi, phi, clamp(blend, 0.0, 1.0));
            if (crossingRadius >= diskInner && crossingRadius <= uDiskOuterRadius) {
                float orbitalDenominator = crossingRadius * crossingRadius * crossingRadius -
                                           3.0 * crossingRadius * crossingRadius +
                                           2.0 * spin * pow(max(crossingRadius, 1.0e-3), 1.5);
                if (orbitalDenominator > 1.0e-5) {
                    float inverseRoot = 1.0 / sqrt(orbitalDenominator);
                    float orbitTime = (pow(crossingRadius, 1.5) + spin) * inverseRoot;
                    float orbitAzimuth = inverseRoot;
                    float emittedEnergy = energy * orbitTime - angularMomentum * orbitAzimuth;
                    float shift = 1.0 / max(abs(emittedEnergy), 1.0e-4);

                    float restTemperature = diskTemperatureAt(crossingRadius, diskInner, uDiskInnerTemperature, spin) *
                                            pow(max(uAccretionRate, 1.0e-3), 0.25);
                    if (restTemperature > 1.0) {
                        float observedTemperature = restTemperature * shift;
                        float density = diskDensityPattern(crossingRadius, crossingPhi, spin, uTime);
                        float radialFade = smoothstep(uDiskOuterRadius, uDiskOuterRadius * 0.72, crossingRadius);

                        vec3 travel = normalize(currentCartesian - previousCartesian);
                        float cosineEmission = abs(travel.y);
                        float scaleHeight = max(uDiskThickness * crossingRadius, 1.0e-4);
                        float slabPath = scaleHeight / max(cosineEmission, 0.02);
                        float opticalDepth = 1.0 - exp(-density * slabPath * 2.2);
                        float rim = smoothstep(0.30, 0.02, cosineEmission) *
                                    smoothstep(diskInner * 2.6, diskInner * 1.02, crossingRadius);

                        float beaming = pow(shift, 4.0);
                        float normalizedTemperature = restTemperature / max(uDiskInnerTemperature, 1.0);
                        float radiance = pow(normalizedTemperature, 4.0) * beaming * opticalDepth * radialFade *
                                         limbDarkening(cosineEmission) * (1.0 + rim * 0.85) * uDiskBrightness;

                        diskColor = blackBodyRadiance(observedTemperature, radiance) * uDiskOpacity;
                        diskHit = true;
                        accumulated += diskColor;
                        break;
                    }
                }
            }
        }

        if (radius > kEscapeRadius) {
            escaped = true;
            escapeDirection = normalize(currentCartesian - previousCartesian);
            break;
        }

        previousCartesian = currentCartesian;
        previousCosine = currentCosine;
        previousRadius = radius;
        previousPhi = phi;
    }

    if (!diskHit && !captured) {
        if (!escaped) {
            escapeDirection = normalize(previousCartesian);
        }
        float backgroundShift = clamp(1.0 / max(energy, 1.0e-3), 0.2, 5.0);
        vec3 sky = sampleDeepSky(escapeDirection, uTime, uSkyDetail);
        accumulated += applySpectralShift(sky, backgroundShift);
    }

    fragColor = vec4(accumulated * uExposure, 1.0);
}
)GLSL";

std::string buildFragmentSource() {
    std::string source = "#version 330 core\n";
    source += kColorCommonSource;
    source += kSkyCommonSource;
    source += kBlackHoleFragmentBody;
    return source;
}

}

Status BlackHolePass::initialize() {
    triangle.initialize();
    const std::string fragmentSource = buildFragmentSource();
    const Status compiled = shader.compile("VoidHeartKerr", kFullscreenVertexSource, fragmentSource.c_str());
    if (!compiled.ok()) return compiled;
    logInfo("voidheart", "Kerr-Raymarcher bereit");
    return statusOk();
}

void BlackHolePass::release() {
    shader.release();
    target.release();
    triangle.release();
}

namespace {

f32 haltonSequence(u32 index, u32 base) {
    f32 result = 0.0f;
    f32 fraction = 1.0f / static_cast<f32>(base);
    u32 cursor = index;
    while (cursor > 0) {
        result += static_cast<f32>(cursor % base) * fraction;
        cursor /= base;
        fraction /= static_cast<f32>(base);
    }
    return result;
}

}

void BlackHolePass::render(const Camera& camera, const BlackHoleRenderParameters& parameters, u32 targetWidth,
                           u32 targetHeight) {
    if (!shader.valid()) return;

    convergenceLimit = parameters.accumulate ? maxValue(parameters.accumulationLimit, 1u) : 1u;
    const f32 scale = parameters.accumulate ? clampValue(parameters.accumulationResolutionScale, 0.25f, 1.0f)
                                            : clampValue(parameters.resolutionScale, 0.25f, 1.0f);
    const u32 width = maxValue<u32>(64, static_cast<u32>(static_cast<f32>(targetWidth) * scale));
    const u32 height = maxValue<u32>(64, static_cast<u32>(static_cast<f32>(targetHeight) * scale));
    if (!target.valid() || target.width() != width || target.height() != height) {
        target.create(width, height, GL_RGBA16F, false);
        sampleIndex = 0;
    }
    if (!parameters.accumulate) sampleIndex = 0;
    if (sampleIndex >= convergenceLimit) return;

    const DVec3 offset = camera.position() - parameters.centerWorldPosition;
    const f64 inverseRadius = 1.0 / parameters.gravitationalRadiusMeters;
    const Vec3 cameraInGravitationalRadii(static_cast<f32>(offset.x * inverseRadius),
                                          static_cast<f32>(offset.y * inverseRadius),
                                          static_cast<f32>(offset.z * inverseRadius));

    const f32 innerRadius = parameters.diskInnerRadius > 0.0f
                                ? parameters.diskInnerRadius
                                : innermostStableCircularOrbit(parameters.spinParameter);

    target.bindForDrawing();
    glDisable(GL_DEPTH_TEST);
    glDisable(GL_CULL_FACE);

    if (sampleIndex == 0) {
        target.clear(0.0f, 0.0f, 0.0f, 1.0f, false);
        glDisable(GL_BLEND);
    } else if (gl().blendColor) {
        const f32 weight = 1.0f / static_cast<f32>(sampleIndex + 1);
        glEnable(GL_BLEND);
        gl().blendColor(0.0f, 0.0f, 0.0f, weight);
        glBlendFunc(GL_CONSTANT_ALPHA, GL_ONE_MINUS_CONSTANT_ALPHA);
    } else {
        target.clear(0.0f, 0.0f, 0.0f, 1.0f, false);
        glDisable(GL_BLEND);
    }

    const f32 jitterX = sampleIndex == 0 ? 0.0f
                                         : (haltonSequence(sampleIndex, 2) - 0.5f) / static_cast<f32>(width);
    const f32 jitterY = sampleIndex == 0 ? 0.0f
                                         : (haltonSequence(sampleIndex, 3) - 0.5f) / static_cast<f32>(height);

    shader.bind();
    shader.setVec2("uPixelJitter", jitterX, jitterY);
    shader.setVec3("uCameraRight", camera.right());
    shader.setVec3("uCameraUp", camera.up());
    shader.setVec3("uCameraForward", camera.forward());
    shader.setVec3("uCameraPosition", cameraInGravitationalRadii);
    shader.setFloat("uTanHalfFieldOfView", std::tan(camera.verticalFieldOfView() * 0.5f));
    shader.setFloat("uAspectRatio", camera.aspectRatio());
    shader.setFloat("uSpin", parameters.spinParameter);
    shader.setFloat("uDiskInnerRadius", innerRadius);
    shader.setFloat("uDiskOuterRadius", parameters.diskOuterRadius);
    shader.setFloat("uDiskInnerTemperature", parameters.diskInnerTemperatureKelvin);
    shader.setFloat("uDiskThickness", parameters.diskThickness);
    shader.setFloat("uDiskOpacity", parameters.diskOpacity);
    shader.setFloat("uDiskBrightness", parameters.diskBrightness);
    shader.setFloat("uJetStrength", parameters.jetStrength);
    shader.setFloat("uAccretionRate", parameters.accretionRate);
    shader.setFloat("uTime", parameters.elapsedSeconds);
    shader.setFloat("uExposure", parameters.exposureScale);
    shader.setFloat("uStepFraction", parameters.stepFraction);
    shader.setInt("uMaximumSteps", static_cast<i32>(parameters.maximumSteps));
    shader.setInt("uIntegratorOrder", parameters.integratorOrder);
    shader.setInt("uSkyDetail", parameters.skyDetail);

    triangle.draw();
    glDisable(GL_BLEND);
    ++sampleIndex;
}

f32 BlackHolePass::horizonRadius(f32 spin) {
    const f32 clamped = clampValue(spin, 0.0f, 0.998f);
    return 1.0f + std::sqrt(maxValue(1.0f - clamped * clamped, 0.0f));
}

f32 BlackHolePass::innermostStableCircularOrbit(f32 spin) {
    const f32 clamped = clampValue(spin, 0.0f, 0.998f);
    const f32 factorOne = 1.0f + std::cbrt(1.0f - clamped * clamped) *
                                     (std::cbrt(1.0f + clamped) + std::cbrt(1.0f - clamped));
    const f32 factorTwo = std::sqrt(3.0f * clamped * clamped + factorOne * factorOne);
    return 3.0f + factorTwo - std::sqrt(maxValue((3.0f - factorOne) * (3.0f + factorOne + 2.0f * factorTwo), 0.0f));
}

f32 BlackHolePass::photonSphereRadius(f32 spin) {
    const f32 clamped = clampValue(spin, 0.0f, 0.998f);
    return 2.0f * (1.0f + std::cos((2.0f / 3.0f) * std::acos(-clamped)));
}

f32 BlackHolePass::ergosphereRadius(f32 spin, f32 polarCosine) {
    const f32 clamped = clampValue(spin, 0.0f, 0.998f);
    const f32 inner = 1.0f - clamped * clamped * polarCosine * polarCosine;
    return 1.0f + std::sqrt(maxValue(inner, 0.0f));
}

f64 BlackHolePass::timeDilationFactor(f64 radiusInGravitationalRadii, f64 spin) {
    const f64 horizon = 1.0 + std::sqrt(maxValue(1.0 - spin * spin, 0.0));
    if (radiusInGravitationalRadii <= horizon) return 0.0;
    const f64 ratio = 2.0 / radiusInGravitationalRadii;
    return std::sqrt(maxValue(1.0 - ratio, 0.0));
}

}
